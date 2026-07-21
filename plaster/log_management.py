import os
import logging

class LogManager:
    def __init__(self, log_path: str, max_bytes: int = 1024 * 1024, target_bytes: int = 900 * 1024):
        self.log_path = log_path
        self.max_bytes = max_bytes        # 1 MB
        self.target_bytes = target_bytes  # 900 KB

    def evaluate_and_rotate(self):
        """Checks log size on refresh and prunes oldest entries if over threshold."""
        if not os.path.exists(self.log_path):
            return

        try:
            current_size = os.path.getsize(self.log_path)
            
            if current_size > self.max_bytes:
                logging.info(f"Log size ({current_size} bytes) exceeds 1MB threshold. Initiating rotation.")
                
                with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                # Prune oldest lines from the beginning until under target size
                while lines and sum(len(line.encode('utf-8')) for line in lines) > self.target_bytes:
                    lines.pop(0)

                # Rewrite the trimmed log back to disk
                with open(self.log_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    
                logging.info(f"Log rotation complete. Trimmed down to approximately {sum(len(line.encode('utf-8')) for line in lines)} bytes.")
                
        except Exception as e:
            logging.error(f"Error during log rotation evaluation: {e}")
