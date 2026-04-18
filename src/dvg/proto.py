import os
import sys
from pathlib import Path

from grpc_tools.protoc import main


def run():
    os.chdir(Path(os.path.dirname(__file__)).parent)
    proto_file = f"./dvg/{sys.argv[1]}.proto"
    print(f"Compiling: {proto_file}")
    main(
        [
            "--proto_path=.",
            "--python_out=.",
            "--grpc_python_out=.",
            proto_file,
        ]
    )
