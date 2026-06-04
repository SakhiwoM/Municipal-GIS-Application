import os
import subprocess
import sys

def launch_external_gis(file_path):
    """
    Locates the system's external GIS installation (QGIS or ArcGIS) 
    and opens the selected vector layer directly inside it for advanced editing.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError("The target spatial file could not be found.")

    try:
        # --- WINDOWS ENVIRONMENT AUTOMATION ---
        if sys.platform == "win32":
            # 1. Try to open via standard system file associations (Default GIS editor)
            try:
                os.startfile(file_path)
                return "Default GIS Application"
            except Exception:
                pass

            # 2. Hardcoded fallback path checking for standard QGIS installations
            common_qgis_paths = [
                r"C:\Program Files\QGIS 3.34.0\bin\qgis-bin.exe",
                r"C:\Program Files\QGIS 3.28.0\bin\qgis-bin.exe",
                r"C:\Program Files\QGIS 3.22.0\bin\qgis-bin.exe",
                r"C:\Program Files\QGIS 3.16.0\bin\qgis-bin.exe",
            ]
            
            for qgis_path in common_qgis_paths:
                if os.path.exists(qgis_path):
                    subprocess.Popen([qgis_path, file_path])
                    return "QGIS Desktop"
            
            raise RuntimeError("No native QGIS installation detected in standard Program Files directories.")

        # --- MACOS ENVIRONMENT AUTOMATION ---
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "QGIS", file_path])
            return "QGIS Desktop"

        # --- LINUX ENVIRONMENT AUTOMATION ---
        else:
            subprocess.Popen(["qgis", file_path])
            return "QGIS Desktop"

    except Exception as e:
        raise RuntimeError(f"OS Execution Layer Failure: {str(e)}")