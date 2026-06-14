# Soniox Dictation

Ditado desktop em tempo real para GNOME/Wayland usando Soniox. No setup atual,
a colagem automática usa `ydotool`/`ydotoold`: o texto final é copiado para o
clipboard com `wl-copy` e o `ydotool` dispara o atalho de colar no app focado.

- `Ctrl+Espaço`: inicia a gravação e cola o resultado com `Ctrl+V`; se a
  gravação já estiver ativa, finaliza.
- `Ctrl+Shift+Espaço`: inicia a gravação e cola o resultado com
  `Ctrl+Shift+V`; se a gravação já estiver ativa, finaliza.
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

Crie um `.env` a partir do exemplo:

```bash
cp .env.sample .env
```

Depois preencha a chave:

```bash
SONIOX_API_KEY=...
```

Sem `SONIOX_YDOTOOL_COMMAND`, o app procura `ydotool` no `PATH`. Sem
`SONIOX_YDOTOOL_SOCKET`, ele usa o socket padrão do `ydotoold`.

A colagem automática sempre tenta usar `ydotool` e mantém a transcrição no
clipboard se falhar. Os atalhos GNOME instalados passam o modo de colagem
automaticamente: `Ctrl+Espaço` usa `Ctrl+V`; `Ctrl+Shift+Espaço` usa
`Ctrl+Shift+V`. Quando o controle é chamado sem modo explícito, o fallback fixo
é `Ctrl+Shift+V`.

## Rodar

```bash
./run.sh
```

Antes de testar a colagem automática, confirme que o `ydotoold` está rodando. Se
você definiu `SONIOX_YDOTOOL_SOCKET`, o daemon precisa usar o mesmo socket.

## Controle

```bash
./scripts/toggle.sh
./scripts/toggle.sh ctrl+v
./scripts/toggle.sh ctrl+shift+v
./scripts/status.sh
./scripts/restart.sh
./scripts/stop.sh
```

`toggle.sh` é o comando usado pelos atalhos GNOME: se o app já estiver rodando,
ele alterna a gravação; se não estiver, inicia o app e começa a gravar. Sem
argumento, usa o fallback fixo `ctrl+shift+v`.

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

Instalar `Ctrl+Espaço` e `Ctrl+Shift+Espaço`:

```bash
./scripts/install-gnome-shortcut.sh
```

Remover:

```bash
./scripts/uninstall-gnome-shortcut.sh
```
