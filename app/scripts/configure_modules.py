import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

from app.app.registry.modules import (
    ALL_MODULES,
    COMMON_ENV_SECTIONS,
    MODULES_BY_NAME,
    MODULE_ENV_SECTIONS,
    normalize_module_names,
)

BLOCKING_COMMON_VARS = ("OPENAI_API_KEY", "MONGO_URI", "MONGO_DB")
PLACEHOLDER_MARKERS = ("tu_", "tu-", "tu.", "_aqui", "tu-dominio", "Resumen corto del negocio")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un archivo .env con la configuracion minima para los modulos elegidos.",
    )
    parser.add_argument(
        "--modules",
        type=str,
        help="Lista separada por comas. Ejemplo: whatsapp,webchat",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".env.modules",
        help="Ruta del archivo de salida. Default: .env.modules",
    )
    parser.add_argument(
        "--from-env",
        type=str,
        default=".env",
        help="Archivo base para reutilizar valores existentes. Default: .env",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Muestra los modulos disponibles y sale.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Si la configuracion esta completa, arranca uvicorn con ese archivo.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host para uvicorn cuando se usa --run. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto para uvicorn cuando se usa --run. Default: 8000",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Activa --reload en uvicorn cuando se usa --run.",
    )
    parser.add_argument(
        "--app",
        type=str,
        default="app.main:app",
        help="App ASGI a ejecutar cuando se usa --run. Default: app.main:app",
    )
    return parser.parse_args()


def read_existing_values(*paths: Path):
    merged = {}
    for path in paths:
        if path.exists():
            values = dotenv_values(path)
            merged.update({key: value for key, value in values.items() if value is not None})
    return merged


def build_sections(selected_modules):
    sections = list(COMMON_ENV_SECTIONS)
    for module_name in selected_modules:
        sections.extend(MODULE_ENV_SECTIONS[module_name])
    return sections


def flatten_sections(sections):
    entries = {}
    for _, section_entries in sections:
        for key, default in section_entries:
            entries[key] = default
    return entries


def render_env(selected_modules, existing_values):
    sections = build_sections(selected_modules)
    rendered_sections = []

    for title, entries in sections:
        lines = [f"# {title}"]
        for key, default in entries:
            if key == "ENABLED_MODULES":
                value = ",".join(selected_modules)
            else:
                value = existing_values.get(key, default)
            lines.append(f"{key}={value}")
        rendered_sections.append("\n".join(lines))

    return "\n\n".join(rendered_sections) + "\n"


def print_available_modules():
    print("Modulos disponibles:")
    for module in ALL_MODULES:
        print(f"- {module.name}: {module.description}")


def is_placeholder_value(value: str):
    if value is None:
        return True
    normalized = str(value).strip()
    if not normalized:
        return True
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def get_blocking_vars(selected_modules):
    blocking = list(BLOCKING_COMMON_VARS)
    for module_name in selected_modules:
        for key in MODULES_BY_NAME[module_name].env_vars:
            if key not in blocking:
                blocking.append(key)
    return tuple(blocking)


def validate_env(selected_modules, env_values):
    missing = []
    blocking_keys = get_blocking_vars(selected_modules)

    for key in blocking_keys:
        value = env_values.get(key)
        if is_placeholder_value(value):
            missing.append(key)

    return missing


def print_validation_summary(selected_modules, missing):
    if missing:
        print("Configuracion incompleta.")
        print("Variables pendientes:")
        for key in missing:
            print(f"- {key}")
        return

    print("Configuracion lista para estos modulos:")
    for module_name in selected_modules:
        print(f"- {module_name}")


def run_uvicorn(args, env_values):
    child_env = os.environ.copy()
    child_env.update({key: str(value) for key, value in env_values.items() if value is not None})

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        args.app,
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        command.append("--reload")

    print("Ejecutando:")
    print(" ".join(command))
    return subprocess.call(command, env=child_env)


def main():
    args = parse_args()

    if args.list:
        print_available_modules()
        return 0

    if not args.modules:
        print("Debes indicar --modules. Ejemplo: --modules whatsapp,webchat")
        return 1

    selected_modules = normalize_module_names(args.modules)
    output_path = Path(args.output)
    source_path = Path(args.from_env)

    existing_values = read_existing_values(source_path, output_path)
    rendered_env = render_env(selected_modules, existing_values)
    output_path.write_text(rendered_env, encoding="utf-8")

    generated_values = read_existing_values(output_path)
    missing = validate_env(selected_modules, generated_values)

    print(f"Archivo generado: {output_path}")
    print(f"Modulos habilitados: {', '.join(selected_modules)}")
    print("Variables por modulo:")
    for module_name in selected_modules:
        module = MODULES_BY_NAME[module_name]
        print(f"- {module.name}: {', '.join(module.env_vars) if module.env_vars else 'sin variables extra'}")

    print_validation_summary(selected_modules, missing)

    if args.run:
        if missing:
            print("No se ejecuta la app hasta completar esas variables.")
            return 1
        return run_uvicorn(args, generated_values)

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
