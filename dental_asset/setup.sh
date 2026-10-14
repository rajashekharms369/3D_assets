#!/usr/bin/env bash
set -euo pipefail
export UV_PYTHON_INSTALL_DIR=/workspace/.dental-tools/uv-python
export UV_CACHE_DIR=/workspace/.dental-tools/uv-cache
mkdir -p /workspace/.dental-tools/blender-user-config /workspace/.dental-tools/blender-user-scripts /workspace/.dental-tools/blender-user-extensions
if [[ ! -x /workspace/.dental-tools/py311/bin/python ]]; then
  uv venv --python 3.11.17 /workspace/.dental-tools/py311
fi
uv pip install --python /workspace/.dental-tools/py311/bin/python bpy==4.3.0 numpy==1.26.4 pillow==12.3.0
cat > /workspace/.dental-tools/run-python.sh <<'RUNNER'
#!/usr/bin/env bash
set -euo pipefail
export BLENDER_USER_CONFIG=/workspace/.dental-tools/blender-user-config
export BLENDER_USER_SCRIPTS=/workspace/.dental-tools/blender-user-scripts
export BLENDER_USER_EXTENSIONS=/workspace/.dental-tools/blender-user-extensions
exec /workspace/.dental-tools/py311/bin/python "$@"
RUNNER
chmod +x /workspace/.dental-tools/run-python.sh
