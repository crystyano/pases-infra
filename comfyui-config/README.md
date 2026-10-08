# comfyui-config

Definicao versionada do ComfyUI da estacao PASES (Cap. 8A do manual).
O ComfyUI em si (`../comfyui/`: clone + .venv) NAO e versionado: reconstroi-se pelo procedimento do Cap. 8A.4.

| Arquivo | Onde e usado (link simbolico apontando para ca) |
|---|---|
| `comfyui.service` | `~/.config/systemd/user/comfyui.service` |
| `extra_model_paths.yaml` | `/srv/pases/comfyui/extra_model_paths.yaml` |

Reinstalar em maquina nova (depois de clonar o ComfyUI e criar o venv):

```bash
ln -sf /srv/pases/comfyui-config/extra_model_paths.yaml /srv/pases/comfyui/extra_model_paths.yaml
mkdir -p ~/.config/systemd/user
ln -sf /srv/pases/comfyui-config/comfyui.service ~/.config/systemd/user/comfyui.service
systemctl --user daemon-reload && systemctl --user enable --now comfyui.service
```
