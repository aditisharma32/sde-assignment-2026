"""Benchmark public_03_load scenario for Scale and Throughput Evaluation (Section 8)."""
import os
import resource
import subprocess
import sys
import time
import httpx


def run_benchmark():
    run_dir = "runs/bench_load"
    db_file = "runs/bench_load_audit.db"
    os.makedirs("runs", exist_ok=True)

    server_cmd = [
        sys.executable,
        "-m",
        "sim",
        "serve",
        "--scenario",
        "scenarios/public_03_load.yaml",
        "--run-dir",
        run_dir,
        "--port",
        "8700",
        "--force",
    ]
    print("Starting simulator server on public_03_load...")
    server_proc = subprocess.Popen(server_cmd)
    sim_url = "http://127.0.0.1:8700"

    try:
        ready = False
        print("Waiting for simulator world and history generation...")
        for i in range(120):
            try:
                r = httpx.get(f"{sim_url}/health", timeout=2.0)
                if r.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(1.0)
        if not ready:
            raise RuntimeError("Simulator failed to start within 120s")

        print("Simulator ready. Starting controller on public_03_load (running 1 full simulated day)...")
        # Run controller with 30-minute steps
        ctrl_cmd = [
            sys.executable,
            "-m",
            "controller.main",
            "--url",
            sim_url,
            "--db",
            db_file,
            "--step",
            "30",
        ]

        t0 = time.perf_counter()
        ctrl_proc = subprocess.Popen(ctrl_cmd)

        # Monitor controller until it finishes or reaches end of day 1 (1440 mins)
        target_minutes = 1440
        last_minute = 0
        peak_rss_mb = 0.0

        while ctrl_proc.poll() is None:
            time.sleep(2.0)
            try:
                st = httpx.get(f"{sim_url}/sim/state", timeout=2.0).json()
                cur_min = st.get("sim_minute", 0)
                last_minute = cur_min
                # Sample memory of controller process
                try:
                    import psutil
                    p = psutil.Process(ctrl_proc.pid)
                    rss = p.memory_info().rss / (1024 * 1024)
                    peak_rss_mb = max(peak_rss_mb, rss)
                except Exception:
                    pass

                elapsed = time.perf_counter() - t0
                print(f"[LOAD BENCH] Sim Minute: {cur_min}/1440 | Elapsed: {elapsed:.1f}s | Events: {st.get('last_event_id', 0)}")
                if cur_min >= target_minutes or st.get("finished"):
                    print("[LOAD BENCH] Reached 1 full simulated day target!")
                    ctrl_proc.terminate()
                    break
            except Exception:
                pass

        total_wall_time = time.perf_counter() - t0
        st = httpx.get(f"{sim_url}/sim/state").json()
        total_events = st.get("last_event_id", 0)
        throughput = total_events / max(total_wall_time, 0.001)

        print("\n" + "="*50)
        print("PUBLIC_03_LOAD BENCHMARK RESULTS")
        print("="*50)
        print(f"Simulated Time Elapsed:     {last_minute} minutes (1 day = 1440 min)")
        print(f"Wall-Clock Time:            {total_wall_time:.2f} seconds ({total_wall_time/60:.2f} minutes)")
        print(f"Total Events Ingested:      {total_events:,}")
        print(f"Ingest Throughput:          {throughput:,.1f} events/second")
        print(f"Peak Memory (RSS):          {peak_rss_mb:.1f} MB (limit 8,192 MB)")
        print(f"Meets Platform SRE target:  {'YES (<10 min/day)' if (total_wall_time/60) < 10.0 else 'NO'}")
        print("="*50 + "\n")

    finally:
        server_proc.terminate()
        server_proc.wait()


if __name__ == "__main__":
    run_benchmark()
