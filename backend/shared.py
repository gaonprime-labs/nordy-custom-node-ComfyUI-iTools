import yaml  # type: ignore
import os
import folder_paths  # type: ignore
import re
import time
import numpy as np  # type: ignore
import torch  # type: ignore
from PIL import Image  # type: ignore
import json
import base64
import io
import subprocess
import sys


def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def base64_to_pil(base64_string):
    header, encoded = base64_string.split(",", 1)  # Remove the data URL header
    image_data = base64.b64decode(encoded)
    return Image.open(io.BytesIO(image_data))


class MyCustomError(Exception):
    def __init__(self, message="Something went wrong"):
        super().__init__(message)


class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")


class FlexibleOptionalInputType(dict):
    def __init__(self, type):
        self.type = type

    def __getitem__(self, key):
        return (self.type,)

    def __contains__(self, key):
        return True


def time_it(func, *args, **kwargs):
    start_time = time.time()  # Record start time
    result = func(*args, **kwargs)  # Call the passed function with arguments
    end_time = time.time()  # Record end time
    print(f"Execution time: {end_time - start_time:.6f} seconds")
    return result


def clean_text(text):
    # Remove duplicate commas
    text = re.sub(r",+", ",", text)

    # Replace any occurrence of " ," with ","
    text = re.sub(r"\s+,", ",", text)

    # Ensure there's a space after commas followed by a word without space
    text = re.sub(r",(\S)", r", \1", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    # Replace any occurrence of ".,", ",." with "."
    text = re.sub(r"\.,|,\.", ".", text)

    # Strip leading and trailing spaces
    return text.strip().replace(" .", ".")


def load_yaml_data(_file_path):
    try:
        # Open the file with UTF-8 encoding
        with open(_file_path, "r", encoding="utf-8") as yaml_file:
            # Load YAML content as Python objects
            _yaml_data = yaml.safe_load(yaml_file)

        # Ensure the data is returned as a list
        if isinstance(_yaml_data, list):
            return _yaml_data
        else:
            raise ValueError("YAML content is not a list of objects.")

    except FileNotFoundError:
        print(f"Error: The file '{_file_path}' was not found.")
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML format. {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


def get_yaml_names(_folder_path):
    names = []

    for file_name in os.listdir(_folder_path):
        if file_name.endswith(".yaml") or file_name.endswith(".yml"):
            names.append(file_name)

    return names


possible_names = ["comfyui-itools", "ComfyUI-iTools"]


def check_detect_project_dir():
    paths = folder_paths.folder_names_and_paths["custom_nodes"][0]
    for path in paths:
        for name in possible_names:
            proj_dir = os.path.join(path, name)
            if os.path.exists(proj_dir):
                return proj_dir
    raise FileNotFoundError("No valid project directory found on the device.")


project_dir = check_detect_project_dir()


def get_user_extra_style_choice():
    try:
        ud_dir = os.path.join(folder_paths.base_path, "user", "default")
        settings_file = os.path.join(ud_dir, "comfy.settings.json")
        with open(settings_file, "r") as file:
            settings = json.load(file)
        return settings.get("iTools.Nodes.More Styles", False)
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


allow_extra_styles = get_user_extra_style_choice()

styles = get_yaml_names(os.path.join(project_dir, "styles"))

if allow_extra_styles:
    more_styles = get_yaml_names(os.path.join(project_dir, "styles", "more examples"))
    styles.extend(x for x in more_styles if x not in styles)


def read_styles(_yaml_data):
    if not isinstance(_yaml_data, list):
        print("Error: input data must be a list")
        return None

    names = []

    for item in _yaml_data:
        if isinstance(item, dict):
            if "name" in item:
                names.append(item["name"])

    return names


def tensor2pil(image):
    return Image.fromarray(
        np.clip(255.0 * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8)
    )


# not used
def tensor2pil_hi(image):
    try:
        # Handle single image
        return Image.fromarray(
            np.clip(255.0 * image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8)
        )
    except:
        # Handle batch of images
        images = [
            Image.fromarray(
                np.clip(255.0 * img.cpu().numpy().squeeze(), 0, 255).astype(np.uint8)
            )
            for img in image
        ]
        return images


def pil2tensor(image):
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)


def pil2mask(image):
    # Convert grayscale image to numpy array
    numpy_array = torch.tensor(np.array(image), dtype=torch.float32)
    # Normalize to binary mask: 0 for transparent (or dark), 1 for opaque (or bright)
    mask = (numpy_array > 0).float()  # Converts values to 1 if > 0, otherwise 0
    # Adding a batch dimension
    if mask.dim() == 2:
        mask = mask.unsqueeze(0)  # Shape: [1, H, W]
    return mask


def get_together_client():
    ud_dir = os.path.join(folder_paths.base_path, "user", "default")
    settings_file = os.path.join(ud_dir, "comfy.settings.json")

    with open(settings_file, "r") as file:
        settings = json.load(file)

    together_api = settings.get("iTools.Nodes. together.ai Api Key", "None")

    try:
        from together import Together  # type: ignore
    except ImportError:
        install_package("together")
        from together import Together  # type: ignore # re-import after installation

    api_key = together_api
    if not api_key or api_key == "None":
        api_key = os.environ.get("TOGETHER_API_KEY")

    if not api_key:
        raise MyCustomError(
            "Together.ai API key not found.\n"
            "Get a free key by signing in at together.ai,\n"
            "then add it in iTools settings or set the TOGETHER_API_KEY environment variable.\n"
            "Finally, restart ComfyUI."
        )

    try:
        client = Together(api_key=api_key)
    except Exception as e:
        raise MyCustomError("Failed to initialize Together client.") from e

    return client
