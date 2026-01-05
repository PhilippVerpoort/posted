from subprocess import run
from pathlib import Path


# Path to project IPython profile
profile_path = Path(__file__).parent.parent / ".ipython" / "profile_docs"

# Ensure profile exists
profile_dir = profile_path.resolve()
if not profile_dir.exists():
    raise FileNotFoundError(f"Profile not found: {profile_dir}")

# Install kernel
run([
    "python", "-m", "ipykernel", "install",
    "--prefix=.venv",
    "--name", "docs",
    "--display-name", "Python (docs)",
    "--env", "IPYTHONDIR", str(profile_dir.parent.resolve()),
    "--profile", "docs",
], check=True)
