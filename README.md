# Soniox Dictation

Ditado desktop em tempo real para GNOME usando Soniox. A colagem automática
funciona tanto em X11 quanto em Wayland:

- **X11** (recomendado/testado): o texto final é copiado para o clipboard (via
  GTK) e o `xdotool` reativa a janela de origem e dispara o atalho de colar.
- **Wayland**: o texto é copiado com `wl-copy` e o `ydotool`/`ydotoold` dispara
  o atalho de colar.

O app detecta a sessão automaticamente: usa `xdotool` em X11 e `ydotool` em
Wayland (com fallback para `ydotool` caso o `xdotool` não esteja disponível).

- `Ctrl+Espaço`: inicia a gravação e cola o resultado com `Ctrl+V`; se a
  gravação já estiver ativa, finaliza e cola com `Ctrl+V`.
- `Ctrl+Shift+Espaço`: inicia a gravação e cola o resultado com
  `Ctrl+Shift+V`; se a gravação já estiver ativa, finaliza e cola com
  `Ctrl+Shift+V`.
- `Enter`: finaliza enquanto a gravação estiver ativa, preservando o modo de
  colagem escolhido no início.
- `Esc`: cancela a gravação atual sem colar nada enquanto a gravação estiver
  ativa.
- Uma janela compacta aparece em cada monitor durante a gravação, com contador
  de tempo.
- Se a colagem automática falhar, a transcrição fica no clipboard.

## Fallback quando a conexão cai

Todo o áudio da gravação é mantido em uma cópia local enquanto você fala. Se a
conexão em tempo real com a Soniox cair (internet oscilando, websocket fechado
etc.), a gravação **continua normalmente** e uma notificação avisa que o modo
fallback foi ativado. Ao finalizar a gravação, o áudio completo é salvo em WAV
e enviado para a rota assíncrona de arquivos da Soniox (upload com novas
tentativas + polling), e o texto é colado como de costume.

Se nem a rota assíncrona funcionar (sem internet nenhuma), o WAV fica
preservado em `~/.cache/soniox-dictation/recordings/` e o caminho aparece na
mensagem de erro, para você não perder o que falou. O modelo do fallback é
derivado de `SONIOX_MODEL` (`stt-rt-v4` → `stt-async-v4`) e pode ser sobrescrito
com `SONIOX_ASYNC_MODEL` no `.env`.

## Requisitos

Comuns às duas sessões:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 pulseaudio-utils
```

- `pulseaudio-utils` traz o `parec`, usado para capturar o áudio do microfone.
- `uv` precisa estar instalado: `./run.sh` cria/sincroniza o ambiente Python com ele.

**Em X11**, instale o `xdotool` (faz a colagem automática):

```bash
sudo apt install xdotool
```

**Em Wayland**, instale o `wl-clipboard` e o `ydotool`/`ydotoold`:

```bash
sudo apt install wl-clipboard ydotool
```

No Wayland, rode o `ydotoold` (o daemon precisa conseguir abrir `/dev/uinput`).
Atenção: o `ydotool` dos repositórios do Ubuntu (0.1.8) é antigo e incompatível
com este app — em Wayland é preciso o `ydotool` 1.x (compilado da fonte ou de um
pacote mais novo).

## Configuração

Crie um `.env` a partir do exemplo:

```bash
cp .env.sample .env
```

Depois preencha a chave:

```bash
SONIOX_API_KEY=...
```

Em X11 não há nada a configurar além da chave: o app usa o `xdotool` do `PATH`.

As variáveis `SONIOX_YDOTOOL_COMMAND` e `SONIOX_YDOTOOL_SOCKET` só valem para o
Wayland: sem a primeira, o app procura `ydotool` no `PATH`; sem a segunda, usa o
socket padrão do `ydotoold`.

A colagem automática mantém a transcrição no clipboard se falhar. Os atalhos
GNOME instalados passam o modo de colagem automaticamente: `Ctrl+Espaço` usa
`Ctrl+V`; `Ctrl+Shift+Espaço` usa `Ctrl+Shift+V`. Quando o controle é chamado
sem modo explícito, o fallback fixo é `Ctrl+Shift+V`.

## Rodar

```bash
./run.sh
```

Em X11 não há daemon a iniciar. Em Wayland, antes de testar a colagem
automática confirme que o `ydotoold` está rodando; se você definiu
`SONIOX_YDOTOOL_SOCKET`, o daemon precisa usar o mesmo socket.

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

Durante a gravação, o app registra temporariamente `Enter` para finalizar e
`Esc` para cancelar. Esses atalhos são removidos quando a gravação termina,
cancela, falha ou quando o app fecha.

Remover:

```bash
./scripts/uninstall-gnome-shortcut.sh
```
