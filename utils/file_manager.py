import os
import shutil

class BO2FileManager:
    def __init__(self, game_path):
        self.game_path = game_path

    def deploy_mod(self, source_file, target_subdir="zone\\all"):
        """Copies custom .ff (maps/zones) or mod files into the BO2 directory."""
        if not os.path.exists(source_file):
            print(f"[-] Source file not found: {source_file}")
            return False

        destination_dir = os.path.join(self.game_path, target_subdir)
        os.makedirs(destination_dir, exist_ok=True)
        
        dest_path = os.path.join(destination_dir, os.path.basename(source_file))
        
        try:
            shutil.copy2(source_file, dest_path)
            print(f"[+] Successfully deployed: {os.path.basename(source_file)} -> {target_subdir}")
            return True
        except Exception as e:
            print(f"[-] Failed to deploy file: {e}")
            return False