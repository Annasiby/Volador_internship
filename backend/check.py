
from pathlib import Path
import onnxruntime as ort

backend_dir = Path(__file__).resolve().parent

model_path = (
    backend_dir
    / "Engine_module"
    / "models"
    / "best_finetuned_model_compatible.onnx"
)

session = ort.InferenceSession(
    str(model_path),
    providers=["CPUExecutionProvider"],
)

print("Model loaded successfully!")

print("Input details:")
for input_info in session.get_inputs():
    print(input_info.name, input_info.shape, input_info.type)

print("Output details:")
for output_info in session.get_outputs():
    print(output_info.name, output_info.shape, output_info.type)
