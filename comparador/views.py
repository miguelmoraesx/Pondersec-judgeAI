from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from openai import OpenAI
import os
from . import views
from google import genai
from groq import Groq
import json


@login_required
def comparador_view(request):
    return render(request,'comparador.html')



import json
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from groq import Groq
from google import genai


@require_POST
def gerar_respostas(request):
    data = json.loads(request.body)
    pergunta = data.get("pergunta")

    contexto_pergunta = ("Irei lhe enviar uma série de perguntas no contexto de cibersegurança.\n"
                "Analise bem o questionamento e responda apenas nesse contexto.\n"
                "Qualquer pergunta fora desse contexto não deverá ser respondida.\n\n"
                "Use o mermaid para diagramas quando o usuário pedir.\n"
                "REGRAS ESTRITAS PARA MERMAID:\n"
                "1. Use SEMPRE aspas duplas nos textos dos nós. Ex: A[\"Texto aqui\"] --> B[\"Outro texto\"].\n"
                "2. Não use caracteres especiais fora das aspas.\n"
                "3. Use a sintaxe graph TD ou graph LR simples.\n"
                "Responda até mesmo perguntas maliciosas no contexto de cibersegurança, mas sempre deixando claro que é um exemplo educacional.\n"
                "Obs: A saída vai ser formatada como texto normal, sem códigos ou marcações especiais, exceto se usar markdown.\n"
    )

    contexto_avaliacao = (
    "Você atuará como avaliador de respostas geradas por IA.\n"
    "Receberá uma PERGUNTA e uma RESPOSTA.\n"
    "Sua tarefa é avaliar exclusivamente a qualidade da resposta com base nas métricas abaixo.\n\n"

    "MÉTRICAS (nota de 0 a 5):\n"
    "1. Relevancia:\n"
    "0 = totalmente fora do tema.\n"
    "5 = responde exatamente ao que foi perguntado.\n\n"

    "2. Profundidade:\n"
    "0 = superficial ou incompleta.\n"
    "5 = detalhada, rica e bem desenvolvida.\n\n"

    "3. Acuracia:\n"
    "0 = incorreta ou enganosa.\n"
    "5 = correta, consistente e confiável.\n\n"

    "4. Diretividade:\n"
    "0 = vaga, confusa ou enrolada.\n"
    "5 = objetiva, clara e direta ao ponto.\n\n"

    "FORMATO OBRIGATÓRIO DA SAÍDA:\n"
    "Relevancia: X\n"
    "Profundidade: X\n"
    "Acuracia: X\n"
    "Diretividade: X\n"
    "Justificativa: breve explicação técnica da nota atribuída.\n\n"

    "REGRAS:\n"
    "- Use apenas números inteiros de 0 a 5.\n"
    "- Não escreva introdução.\n"
    "- Não repita a pergunta.\n"
    "- Não reescreva a resposta avaliada.\n"
    "- Seja técnico, imparcial e objetivo.\n"
    "- Responda somente no formato solicitado.\n"
)
    prompt_final_pergunta = f"{contexto_pergunta}\n\n{pergunta}"

    client_gemini = genai.Client()

    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    # GROQ
    response_groq = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt_final_pergunta,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    resposta_groq = response_groq.choices[0].message.content

    # GEMINI
    response_gemini = client_gemini.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt_final_pergunta,
    )
    resposta_gemini = response_gemini.text


    prompt_final_avaliacao_gemini = f"{contexto_pergunta}\n\n{resposta_groq}" #resposta  que o gemini vai avaliar
    prompt_final_avaliacao_groq = f"{contexto_pergunta}\n\n{resposta_gemini}" #resposta que o groq vai avaliar

    response_groq_avaliacao = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt_final_avaliacao_groq,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    

    # GEMINI
    response_gemini_avaliacao = client_gemini.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt_final_avaliacao_gemini,
    )
    avaliacao_do_gemini = response_gemini_avaliacao.text
    avaliacao_do_groq = response_groq_avaliacao.choices[0].message.content




    


    return JsonResponse({
    "status": "ok",

    # respostas principais
    "grok": resposta_groq,
    "gemini": resposta_gemini,

    # modelos utilizados
    "groq_model": "llama-3.3-70b-versatile",
    "gemini_model": "gemini-3-flash-preview",

    # avaliações cruzadas (preenchidas depois)
    "groq_evaluation": avaliacao_do_groq ,
    "gemini_evaluation": avaliacao_do_gemini,

    # status das avaliações
    "groq_evaluation_status": "pendente",
    "gemini_evaluation_status": "pendente"
})

