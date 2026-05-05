# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class LLM(models.Model):
    modelo = models.CharField(max_length=100)
    api_key = models.TextField(max_length=500)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.modelo
    
class Resposta(models.Model):
    llm = models.ForeignKey(LLM, on_delete=models.CASCADE)
    conteudo_resposta = models.TextField(max_length=1000)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.conteudo
    
class Pergunta(models.Model):
    conteudo = models.TextField(max_length=1000)
    resposta = models.ForeignKey(Resposta, conteudo=Resposta.conteudo_resposta, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Pergunta - {self.conteudo} | Resposta - {self.resposta}"
    
class Avaliacoes(models.Model):
    llm_avaliada = models.ForeignKey(
                    LLM,
                     
                                      )
