import subprocess

def check():
    try:
        res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.splitlines()
        for line in lines:
            if "LISTENING" in line:
                for port in [":80 ", ":8000 ", ":8001 ", ":3307 "]:
                    if port in line:
                        print(line)
    except Exception as e:
        print(f"Error running netstat: {e}")

check()
