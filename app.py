def enviar_notificacao_push(titulo, mensagem):
    try:
        import time
        msg_id = str(int(time.time()))
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=mensagem.encode('utf-8'),
            headers={
                "Title": titulo.encode('utf-8'),
                "Priority": "5", # Prioridade Máxima
                "Tags": "rotating_light,warning,loud_sound", # O 'loud_sound' ajuda o Android a entender que deve tocar
                "X-Message-ID": msg_id,
                "X-Priority": "5"
            }, 
            timeout=5
        )
    except:
        pass
