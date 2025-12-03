from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class DocumentScannerHandler(FileSystemEventHandler):
    def __init__(self, queue):
        self.queue = queue

    def on_modified(self, event):
        if not event.is_directory:
            self.queue.put(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self.queue.put(event.src_path)

def start_scanner_agent(path, queue):
    event_handler = DocumentScannerHandler(queue)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    print("📂 Scanner Agent watching:", path)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
