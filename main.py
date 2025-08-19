from fastapi import FastAPI
from handlers import router as handlers_router
from pathlib import Path
import shutil
import logging

app = FastAPI()


@app.on_event("startup")
def ensure_writable_data_copy():
	"""Ensure there's a writable copy of `data.json` in /tmp on platforms
	(like Vercel) where the project tree is read-only. If `/tmp/data.json`
	doesn't exist, copy the repository `data.json` there so the app can
	read/write it at runtime."""
	try:
		tmp_path = Path("/tmp/data.json")
		if not tmp_path.exists():
			src = Path(__file__).parent / "data.json"
			if src.exists():
				shutil.copy2(src, tmp_path)
				logging.info(f"Copied data.json to {tmp_path}")
			else:
				logging.warning("Repository data.json not found; skipping copy to /tmp")
	except Exception as e:
		# Don't crash startup for copy errors; log and continue. In Vercel the
		# platform may not allow /tmp writes in some contexts — apps should
		# still function in read-only mode.
		logging.exception("Failed to prepare /tmp/data.json: %s", e)


app.include_router(handlers_router) # Loading handlers and routes

