import os, shutil, subprocess, time
SRC = "/Users/shine/videoatexto"
KD = "/Users/shine/kDrive/Dropbox/Ministry of Innovation/1 BiK/Administración/Colaboraciones, financiación, compras/Formaciones/0. Conocimiento Albert"
ref = os.path.getmtime(os.path.join(SRC, "urls_claude_streams_20260610.txt"))
copied = 0
while True:
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".knowledge.md"): continue
        p = os.path.join(SRC, f)
        try:
            if os.path.getmtime(p) < ref: continue
        except OSError: continue
        dst = os.path.join(KD, f)
        if not os.path.exists(dst):
            try:
                shutil.copy2(p, dst); copied += 1
                print(f"copiado [{copied}]: {f}", flush=True)
            except Exception as e:
                print(f"COPY-FAIL {f}: {e}", flush=True)
    if subprocess.run(["pgrep","-f","cli_pipeline.py"], capture_output=True).returncode != 0:
        print(f"FIN — pipeline terminado. Copiados: {copied}", flush=True)
        break
    time.sleep(120)
