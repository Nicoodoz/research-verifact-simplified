# 032 continuation engineering record

The user asked to continue execution through Remote Desktop Commander.
The existing NLI worker was found running; no duplicate worker was launched.
Five synthetic preflight tests passed (PowerShell classified unittest stderr as NativeCommandError, but the command exit code was 0).
The existing NLI process then exited with conda exit code 1, without a captured Python traceback. The exact native failure cause is unknown.
Last observed cache progress before exit was 52,520 of 54,236 distinct pairs; completed pairs were already flushed to disk.
Last observed GPU usage was 5,455 of 6,144 MiB, with 100% utilization, and progress on long windows was much slower.
The pending continuation correctly refused to start training without a completed NLI manifest.

Only compute batch size is restored from 16 to the original 4. The earlier override and status are preserved here.
The original NLI code, model revision, input pair construction, projected features, training configuration and patient split are not changed.
Finished NLI rows are reused; unfinished rows are computed once on continuation. Floating-point values can differ slightly with batch composition; no bitwise-equivalence claim is made.
No training or confirmation scoring had run at the time of this recovery.
No paid APIs, clinical uploads, credential reads, or changes to main/029 environments.
The raw failure output remains in nli_run002.log and the corresponding terminal session.
Next execution uses run032.py --resume so that training cannot consume an incomplete NLI cache.
