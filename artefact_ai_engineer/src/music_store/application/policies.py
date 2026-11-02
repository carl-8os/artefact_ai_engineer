"""Versioned, human-reviewed customer-facing facts from policy manual v2.1.

The internal PDF is intentionally not redistributed. Section numbers preserve traceability.
"""
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class Policy:
    topic: str
    text: str
    section: str


POLICIES = (
    Policy('address location store phone contact endereco localizacao onde fica loja telefone contato', 'Store: Rua 14 de Maio, 3200, Centro, Campo Grande/MS, postal code 79202-333. Phone: (67) 3341-4444.', '1.2'),
    Policy('hours opening closing saturday sunday holidays horario funcionamento abre fecha aberto expediente sabado domingo feriado', 'Monday–Friday: 09:00–18:00; Saturday: 09:00–13:00; closed Sundays and holidays. Confirm exceptional hours with the team.', '2'),
    Policy('payment pix debit credit boleto discount pagamento pagar debito credito forma desconto', 'PIX upfront: 5% off the regular list price; cannot be combined with promotions. Debit upfront; boleto upfront (clearing may take up to 3 business days). Credit card: up to 12 installments, subject to the specific minimum-payment rules.', '3'),
    Policy('installments split credit minimum parcelamento parcelas dividir credito prestacao vezes juros', 'The manual is inconsistent: its overview mentions a BRL 100 minimum installment; section 3.1 says up to 3 installments with no minimum (with a caveat below BRL 50), 4–6 installments with a BRL 80 minimum each, and 7–12 installments with a BRL 100 minimum each. Confirm low-value payments with staff; never guarantee approval. Split payment methods only for purchases above BRL 2,000.', '3, 3.1'),
    Policy('return refund cancel regret online purchase arrependimento devolucao devolver desisti desistir cancelar reembolso compra online', 'For online purchases, customers may withdraw within 7 calendar days of receipt. The store pays return shipping. The manual requests original packaging, unused condition and included manuals/accessories, and states refunds to the original payment method within 10 business days. These conditions must not override statutory consumer rights; refer disputes to staff.', '4.1'),
    Policy('exchange preference color model troca preferencia modelo cor tamanho', 'Preference exchanges: within 7 days, with the product in perfect condition and original packaging, subject to availability; price differences may apply.', '4.3'),
    Policy('defect faulty warranty broken exchange stopped working not working malfunction protected guarantee guitar troca defeito problema quebrado garantia fabricante', 'Internal defective-item exchange procedure: within 30 days of purchase; after that the store may facilitate manufacturer support. The manual also recognizes a 90-day statutory warranty for durable goods from receipt. Do not suggest that statutory rights end after 30 days.', '4.2, 8.1, 8.2'),
    Policy('exceptions custom clearance mouthpieces exchange excecao troca personalizado liquidacao boquilha', 'The manual excludes preference exchanges for custom-adjusted instruments, final-sale clearance items and mouthpieces. Statutory defect and withdrawal rights must be assessed separately.', '4.4'),
    Policy('shipping delivery metro free cost campo grande frete entrega envio prazo transporte gratis custo', 'Within metropolitan Campo Grande, shipping is free for orders strictly above BRL 500; below BRL 500 it costs BRL 35. Estimated delivery: 1–3 business days. The exact BRL 500 boundary is not specified; confirm with staff.', '5.1'),
    Policy('shipping delivery courier tracking pac sedex jadlog frete correios rastreamento outras cidades seguro', 'Other cities: PAC 5–12 business days; SEDEX 2–5; Jadlog 3–8. Price depends on postal code, weight and dimensions; large instruments may require a quote. Shipments are insured; tracking is provided after dispatch.', '5.2, 5.3'),
    Policy('promotions offers discount original price pix promocao oferta desconto campanha preco original estoque', 'Promotions cannot be combined with one another or with PIX discounts. Only active promotions apply and are subject to stock. Show original price and discount percentage; do not promise expired offers.', '6'),
    Policy('whatsapp human support complaints atendimento reclamacao falar pessoa atendente humano', 'Customer service WhatsApp: (67) 3321-4500 during store hours. Complaints should be referred to the team, with a stated response target of 24 business hours; this prototype does not file complaints.', '7'),
    Policy('accessories strings cables picks cases pedals amplifiers acessorios cordas cabos palhetas pedais amplificadores vende', 'The store sells musical instruments only, not accessories such as strings, picks, cables, cases, pedals or amplifiers.', '1, 7.1'),
    Policy('privacy personal data consent lgpd privacidade dados pessoais excluir consentimento', 'Personal data is used for orders, operational communication and legal obligations; marketing requires consent. Refer personal-data deletion requests to human customer support.', '9'),
)

STOPWORDS = {'the','is','are','what','when','where','can','does','do','my','your','for','with','how','much','about','please','a','o','e','de','da','do','dos','das','um','uma','para','por','com','em','no','na','qual','quais','como','eu','me','meu','minha','vocês','voces','quero','preciso','sobre','tem','que','se','é','eh'}
SYNONYMS = {
    'abrem':'abre', 'abertura':'abre', 'fecham':'fecha', 'funcionam':'funcionamento',
    'endereço':'endereco', 'local':'localizacao', 'localizado':'localizacao',
    'parcelar':'parcelamento', 'parcelado':'parcelamento', 'prestacoes':'prestacao',
    'devolver':'devolucao', 'devolvo':'devolucao', 'devolvido':'devolucao',
    'arrepender':'arrependimento', 'arrependi':'arrependimento',
    'trocar':'troca', 'troco':'troca', 'defeituoso':'defeito', 'estragou':'defeito',
    'entregam':'entrega', 'enviar':'envio', 'transportadora':'transporte',
    'desconto':'desconto', 'promocoes':'promocao', 'garantias':'garantia',
    'atendente':'atendimento', 'falar':'falar',
    'opening':'hours', 'open':'hours', 'closing':'hours', 'opens':'hours',
    'returns':'return', 'returned':'return', 'refunds':'refund',
    'shipping':'delivery', 'shipped':'delivery', 'deliver':'delivery',
    'warranties':'warranty', 'instruments':'instrument',
}


def _tokens(value: str) -> set[str]:
    plain = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    return {SYNONYMS.get(w, w) for w in re.findall(r'[a-z0-9]+', plain) if len(w) > 1 and w not in STOPWORDS}


def find_policies(message: str, limit: int = 3) -> list[Policy]:
    if limit < 1:
        return []
    words = _tokens(message)
    scores = [(len(words & _tokens(p.topic)), index, p) for index, p in enumerate(POLICIES)]
    return [p for score, _, p in sorted(scores, key=lambda row: (-row[0], row[1])) if score > 0][:limit]
