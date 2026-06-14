# Soniox Dictation

Ditado desktop em tempo real para GNOME/Wayland usando Soniox. No setup atual,
a colagem automática usa `ydotool`/`ydotoold`: o texto final é copiado para o
clipboard com `wl-copy` e o `ydotool` dispara o atalho de colar no app focado.

- `Ctrl+Espaço`: inicia ou finaliza a gravação pelo atalho GNOME.
- `Enter`: finaliza enquanto o overlay de gravação estiver ativo.
- `Esc`: cancela a gravação atual sem colar nada.
- Um overlay compacto aparece durante a gravação, com contador de tempo.
- Se a colagem automática falhar, a transcrição fica no clipboard.

## Requisitos

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 pulseaudio-utils wl-clipboard
```

O projeto também espera que `uv` esteja instalado, porque `./run.sh` cria/sincroniza
o ambiente Python com ele.

Para a colagem automática no Wayland, instale e rode `ydotool`/`ydotoold`.
O daemon precisa conseguir abrir `/dev/uinput`.

## Configuração

Crie um `.env` na raiz do projeto:

```bash
SONIOX_API_KEY=...
SONIOX_LANGUAGE_HINTS=pt,en
SONIOX_MODEL=stt-rt-v4

SONIOX_INJECT_BACKEND=ydotool
SONIOX_PASTE_SHORTCUT=ctrl+shift+v
SONIOX_YDOTOOL_COMMAND=/usr/local/bin/ydotool-v1.0.4
SONIOX_YDOTOOL_SOCKET=/tmp/.ydotool_socket
```

`SONIOX_PASTE_SHORTCUT` controla o atalho enviado pelo `ydotool`. Use
`ctrl+shift+v` para apps/terminais que colam sem formatação, ou `ctrl+v` quando
esse for o atalho correto no app focado.

Opções adicionais:

```bash
SONIOX_COPY_ONLY=false
SONIOX_RESTORE_CLIPBOARD=false
SONIOX_SAMPLE_RATE=16000
SONIOX_CHANNELS=1
SONIOX_AUDIO_COMMAND=
SONIOX_DEBUG=false
```

`SONIOX_INJECT_BACKEND` aceita:

- `ydotool`: backend usado neste setup. Tenta colar com `ydotool` e mantém o
  texto no clipboard se falhar.
- `clipboard`: nunca tenta colar automaticamente; só copia a transcrição.

O backend `ydotool` usa keycodes Linux, então foi pensado para `ydotool` `v1.x`.
Se usar uma versão local, aponte `SONIOX_YDOTOOL_COMMAND` para o binário.

## Rodar

```bash
./run.sh
```

Antes de testar a colagem automática, confirme que o `ydotoold` está rodando com
o mesmo socket configurado em `SONIOX_YDOTOOL_SOCKET`.

Modos úteis:

```bash
./run.sh --copy-only
./run.sh --debug
```

## Controle

```bash
./scripts/toggle.sh
./scripts/status.sh
./scripts/restart.sh
./scripts/stop.sh
```

`toggle.sh` é o comando usado pelo atalho GNOME: se o app já estiver rodando,
ele alterna a gravação; se não estiver, inicia o app e começa a gravar.

## Autostart

Instalar:

```bash
./scripts/install-autostart.sh
```

Remover:

```bash
./scripts/uninstall-autostart.sh
```

Logs:

```bash
~/.cache/soniox-dictation/autostart.log
~/.cache/soniox-dictation/manual-restart.log
```

## Atalho GNOME

Instalar `Ctrl+Espaço`:

```bash
./scripts/install-gnome-shortcut.sh
```

Remover:

```bash
./scripts/uninstall-gnome-shortcut.sh
```
