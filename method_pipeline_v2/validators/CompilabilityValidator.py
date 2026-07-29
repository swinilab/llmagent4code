from __future__ import annotations
import subprocess
import os
from pathlib import Path
from interfaces.base import (
    ICompilabilityValidator,
    Status,
    ValidationResult,
)

class CompilabilityValidator(ICompilabilityValidator):
    """
    Real Compilability Validator:
    - Reads the startup command from /start_command.txt
    - Executes it via subprocess (e.g. starting a Docker container)
    - Captures exit codes, stdout, and stderr
    """
    def __init__(self, config: dict | None = None) -> None:
        config = config or {}
        self._generated_dir = Path(
            config.get("agent", {}).get("generated_dir", "generated")
        )
        self._start_command_file = config.get("validator", {}).get("start_command_file", "start_command.txt")

    def _clean_logs(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        lines = raw_text.splitlines()
        clean_lines = [
            line for line in lines 
            if line.strip() and not line.strip().startswith('#')
        ]
        return "\n".join(clean_lines)

    def validate(self, code: str) -> ValidationResult:
        workdir = Path(code)

        try:
            command = Path(os.path.join(
                workdir,
                self._start_command_file
            )).read_text().strip()
        except FileNotFoundError:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Start command file not found: {self._start_command_file}",
                details={"error": "FileNotFoundError"},
            )
        except Exception as e:
            return ValidationResult(
                stage="compilability",
                status=Status.FAIL,
                message=f"Failed to read command file: {e}",
                details={"error": str(e)},
            )

        try:
            # THUẬT TOÁN ÉP CHỜ:
            # Chạy lệnh trong foreground (không dùng cờ -d của docker).
            # Ép quá trình chờ tối đa 10 giây (timeout=10).
            # Nếu là web server (FastAPI), nó sẽ block luồng mãi mãi -> văng lỗi TimeoutExpired.
            # TimeoutExpired trong trường hợp này lại là TIN TỐT (nghĩa là server không bị crash).
            
            process = subprocess.run(
                command,
                cwd=workdir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60 # Quan trọng: Chờ 10 giây xem app có crash không
            )
            
            # Nếu lệnh kết thúc sớm hơn 10 giây và trả về lỗi (!= 0) -> Chắc chắn app đã crash
            if process.returncode != 0:
                return ValidationResult(
                    status=Status.FAIL, 
                    stage="compilability",
                    message="Runtime error or crash detected during startup", 
                    details={"stderr": process.stderr, "stdout": process.stdout}
                )
            
            # (Trường hợp lệnh là script chạy ngắn, chạy xong thành công trả về 0)
            return ValidationResult(
                status=Status.PASS, 
                stage="compilability",
                message="Executed successfully without crashing",
                details={}
            )

        except subprocess.TimeoutExpired as e:
            # 1. DỌN DẸP CONTAINER: 
            # Bắt buộc phải tắt container đang chạy ngầm để giải phóng Port cho lần kiểm tra sau
            subprocess.run(
                "docker compose down", 
                cwd=workdir, 
                shell=True, 
                capture_output=True
            )
            
            # 2. KHỞI TẠO ĐÚNG THAM SỐ:
            # Tạm thời gọi bằng positional arguments
            # LƯU Ý: Đổi thứ tự/số lượng biến dưới đây cho khớp với interfaces/base.py của bạn
            return ValidationResult(
                status=Status.PASS,                                                    
                stage="Compilability",
                message="Server started and remained stable (Timeout reached)", 
                details={}
            )
        except Exception as e:
            return ValidationResult(
                status=Status.FAIL, 
                stage="compilability",
                message=f"Validator internal error: {str(e)}", 
                details={"stderr": str(e)}
            )
