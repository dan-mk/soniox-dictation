# Soniox Dictation

Ditado desktop em tempo real usando Soniox, GNOME Wayland e RemoteDesktop portal.

- `Ctrl+Espaço`: inicia a gravação.
- `Enter`: finaliza enquanto o overlay de gravação estiver ativo.
- A transcrição final vai para o clipboard com `wl-copy`.
- O GNOME RemoteDesktop portal envia `Ctrl+Shift+V` para colar no campo focado.
- Um overlay compacto no rodapé mostra quando a gravação está ativa.

## Requisitos

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 pulseaudio-utils wl-clipboard
```

A chave precisa estar em `.env`:

```bash
SONIOX_API_KEY=...
```

Opções úteis:

```bash
SONIOX_LANGUAGE_HINTS=pt,en
SONIOX_MODEL=stt-rt-v4
SONIOX_MAX_ENDPOINT_DELAY_MS=500
SONIOX_PORTAL_PASTE_SHORTCUT=ctrl+shift+v
```

## Rodar

```bash
./run.sh
```

Na primeira execução, o GNOME pode pedir permissão de controle remoto/teclado. Autorize.

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
