# blender-config — Blender 5.0.1 da estacao PASES (Cap. 8A.12 do manual)

O Blender em si (`/srv/pases/blender/`, 1,6 GB) NAO e versionado; reconstroi-se assim (sem sudo):

```bash
mkdir -p /srv/pases/blender && cd /srv/pases/blender
curl -L -C - --fail -O https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz   # 374 154 072 bytes
echo "8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09  blender-5.0.1-linux-x64.tar.xz" | sha256sum -c -
tar -xJf blender-5.0.1-linux-x64.tar.xz
/srv/pases/blender/blender-5.0.1-linux-x64/blender --version
```

Uso sem interface: `blender -b --factory-startup --python script.py`.

| Script | Funcao |
|---|---|
| `inspeciona.py` | Importa o FBX e lista objetos, ossos, grupos de vertices, materiais e animacoes |
| `render_teste.py` | Renderiza imagens do personagem em poses das animacoes (Cycles, GPU 5060 Ti) |
| `render_clipe.py` | Renderiza uma animacao inteira em PNGs (depois `ffmpeg` monta o MP4) |

Os scripts esperam o FBX extraido em `/scratch/texugo_3d/fbx/` (do `modelo3d/Tripo-export/Bolado.zip` do projeto Texugo Bolado)
e gravam em `/scratch/texugo_3d/`. Ajuste os caminhos se mudar de pasta.
