# Soniox Dictation

Ditado desktop em tempo real usando Soniox, GNOME Wayland e injeção de atalho por `ydotool` ou RemoteDesktop portal.

- `Ctrl+Espaço`: inicia a gravação.
- `Enter`: finaliza enquanto o overlay de gravação estiver ativo.
- A transcrição final vai para o clipboard com `wl-copy`.
- No Wayland, o GNOME RemoteDesktop portal envia `Ctrl+Shift+V` para colar no campo focado.
- `ydotool` pode ser usado como backend alternativo, desde que o `ydotoold` esteja estável.
- Um overlay compacto centralizado mostra quando a gravação está ativa.

## Requisitos

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 pulseaudio-utils wl-clipboard
```

Para colar sem o RemoteDesktop portal no Wayland, instale e rode `ydotool`/`ydotoold`.
O daemon precisa conseguir abrir `/dev/uinput`.

A chave precisa estar em `.env`:

```bash
SONIOX_API_KEY=...
```

Opções úteis:

```bash
SONIOX_LANGUAGE_HINTS=pt,en
SONIOX_MODEL=stt-rt-v4
SONIOX_MAX_ENDPOINT_DELAY_MS=500
SONIOX_INJECT_BACKEND=portal
SONIOX_PORTAL_PASTE_SHORTCUT=ctrl+shift+v
SONIOX_YDOTOOL_COMMAND=ydotool
SONIOX_YDOTOOL_SOCKET=/tmp/.ydotool_socket
```

`SONIOX_INJECT_BACKEND` aceita:

- `portal`: tenta RemoteDesktop portal e mantém o texto no clipboard se falhar.
- `auto`: tenta `ydotool`, depois RemoteDesktop portal, depois só clipboard.
- `ydotool`: tenta apenas `ydotool` e mantém o texto no clipboard se falhar.
- `clipboard`: nunca tenta colar automaticamente.

Para usar uma versão local do `ydotool`, aponte `SONIOX_YDOTOOL_COMMAND` para o binário.
O backend `ydotool` usa keycodes Linux, então funciona com `ydotool` `v1.x`.

## Rodar

```bash
./run.sh
```

Se o backend usado for `portal`, na primeira execução o GNOME pode pedir permissão de controle remoto/teclado. Autorize.

## Controle

```bash
./scripts/status.sh
./scripts/restart.sh
./scripts/stop.sh
```

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

Instalar `Ctrl+Espaço` no GNOME:

```bash
./scripts/install-gnome-shortcut.sh
```

Remover:

```bash
./scripts/uninstall-gnome-shortcut.sh
```
