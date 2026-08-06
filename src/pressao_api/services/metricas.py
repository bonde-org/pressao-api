from datetime import datetime
from pressao_api.schemas.acao import MetricaQualidadeEnum
import structlog

logger = structlog.get_logger()

class CalculadoraMetricas:
    """Calculadora de métricas de qualidade."""
    
    @staticmethod
    def calcular_qualidade(tempo_resposta_seg: int) -> MetricaQualidadeEnum:
        """
        Calcula métrica de qualidade baseada no tempo de resposta.
        
        Regras:
        - < 5s: suspeita (pode ser automatizado)
        - 5s a 60s: alta
        - 60s a 120s: media
        - > 120s: baixa
        """
        if tempo_resposta_seg < 5:
            return MetricaQualidadeEnum.SUSPEITA
        elif tempo_resposta_seg <= 60:
            return MetricaQualidadeEnum.ALTA
        elif tempo_resposta_seg <= 120:
            return MetricaQualidadeEnum.MEDIA
        else:
            return MetricaQualidadeEnum.BAIXA
    
    @staticmethod
    def calcular_tempo_resposta(criado_em: datetime, confirmado_em: datetime) -> int:
        """Calcula tempo de resposta em segundos."""
        delta = confirmado_em - criado_em
        return int(delta.total_seconds())

calculadora = CalculadoraMetricas()