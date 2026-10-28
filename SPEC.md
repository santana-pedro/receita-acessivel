# Receita Acessível — Especificações do Projeto

## Visão Geral

Aplicação web que traduz receitas médicas para dois públicos:
- **Deficiência visual** — layout acessível com fontes grandes e alto contraste
- **Analfabetismo** — conteúdo reescrito com linguagem simples, emojis e símbolos visuais

O médico faz o upload da receita, escolhe o modo de tradução, e a IA processa e exibe o resultado. O resultado pode ser baixado em PDF, Word (.docx) ou TXT.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | HTML5 + CSS3 + JavaScript (vanilla, sem frameworks) |
| Backend | Python 3.11+ + FastAPI |
| IA | Google Gemini 1.5 Flash via `google-generativeai` (gratuito) |
| Leitura de PDF | `pdfplumber` |
| Leitura de Word | `python-docx` |
| OCR (fallback) | `pytesseract` + Tesseract instalado no sistema |
| Geração de PDF | `WeasyPrint` |
| Geração de Word | `python-docx` |
| Servidor de arquivos estáticos | FastAPI `StaticFiles` |

**Sem custos.** Toda a stack é gratuita. A API Key do Gemini é obtida em aistudio.google.com sem cartão de crédito.

---

## Estrutura de Pastas

```
receita-acessivel/
├── backend/
│   ├── main.py               # FastAPI app, rotas
│   ├── ai.py                 # Integração com Gemini
│   ├── extractor.py          # Extração de texto (PDF, Word, txt)
│   ├── exporter.py           # Geração dos arquivos de download
│   ├── prompts.py            # Prompts do sistema para cada modo
│   └── requirements.txt
├── frontend/
│   ├── index.html            # Página principal
│   ├── style.css             # Estilos globais
│   └── app.js                # Lógica do frontend
├── .env.example              # Exemplo de variáveis de ambiente
└── README.md
```

---

## Funcionalidades

### Entrada da receita
O usuário escolhe entre duas formas (abas):
- **Enviar arquivo**
  - Formatos aceitos: `.pdf`, `.docx`, `.txt` — **imagens (`.jpg`, `.png` etc.) não são aceitas**
  - Limite de tamanho: 10 MB
  - O PDF pode vir escaneado (baixa qualidade) — usar OCR como fallback
- **Digitar receita** — campo de texto onde a receita é digitada ou colada (máx. 20.000 caracteres)

### Modos de tradução
1. **Deficiência Visual**
   - O texto da receita é formatado com fonte mínima de 32px
   - Fonte: Arial ou sans-serif
   - Alto contraste: fundo branco, texto preto (#111)
   - Espaçamento entre linhas: 2.0
   - A IA reescreve o conteúdo de forma clara, sem abreviações, em frases curtas
   - O download em PDF preserva esse layout acessível

2. **Analfabetismo**
   - O paciente deve entender a receita **somente pelos emojis e símbolos** (sem precisar ler)
   - Cada linha tem duas partes: símbolos grandes (para o paciente) | texto curto e pequeno
     (para o farmacêutico ou familiar que atende o paciente)
   - Cada remédio recebe uma cor (🔴 🔵 🟢 …) e um símbolo de forma (💊 comprimido, 🥄 xarope,
     💧 gotas, 👃 spray…), para o paciente associar o cartão à caixa
   - Horários em números no formato do celular + período (☀️ ⏰ 08:00, 🌙 ⏰ 20:00) — nunca relógio
     analógico, que o paciente pode não saber ler; intervalos com ⏳ (⏳ 12 = de 12 em 12 horas);
     intervalo mínimo de remédio "se precisar" com ✋ ⏳
   - Quantidades: o símbolo é repetido (💊💊 = 2 comprimidos); números só para medidas (💧 40, 🥄 15 ml)
   - O nome do remédio aparece em texto no topo do cartão (não há como convertê-lo em símbolo)
   - Cada cartão traz somente o que a receita diz sobre aquele remédio: nada é inventado nem
     copiado de outro remédio
   - Layout em "cards" visuais, um por medicamento

### Processamento da IA
- O backend detecta o tipo do arquivo e extrai o texto:
  - `.txt` → leitura direta
  - `.docx` → `python-docx`
  - `.pdf` com texto digital → `pdfplumber`
  - `.pdf` escaneado → envio direto do PDF ao Gemini (multimodal), com Tesseract como fallback
- Texto digitado → enviado diretamente
- O texto extraído é enviado ao Gemini com o prompt do modo escolhido

### Prompts do sistema

**Modo Deficiência Visual:**
```
Você é um assistente de saúde. Receberá uma receita médica com possíveis abreviações
e termos técnicos. Sua tarefa:
1. Interprete todas as abreviações médicas (VO, EV, SOS, BID, TID, QID, cp, gt, amp, etc.)
2. Reescreva a receita de forma clara, sem abreviações, em frases curtas e simples
3. Separe cada medicamento claramente com uma linha em branco
4. Use linguagem acessível, mas mantenha as informações completas e precisas
5. Retorne apenas o texto da receita traduzida, sem explicações adicionais
Receita:
```

**Modo Analfabetismo:**
```
Você é um assistente de saúde. Receberá uma receita médica. Transforme-a para um paciente
que NÃO sabe ler: ele deve entender tudo só pelos emojis e símbolos. Ao lado de cada linha de
símbolos vai um texto curto, para o farmacêutico ou familiar que ajuda o paciente.

Regras:
1. Interprete todas as abreviações médicas e converta intervalos em horários do dia.
   Se a receita indicar horários, use-os; senão, use estes horários padrão:
   - 1x ao dia / 24/24h: 8h
   - 12/12h: 8h e 20h
   - 8/8h: 6h, 14h e 22h
   - 6/6h: 6h, 12h, 18h e 24h
   - 4/4h: 6h, 10h, 14h, 18h, 22h e 2h
2. Toda linha tem o formato: [símbolos] | [texto curto]
   - antes da barra: SOMENTE emojis, símbolos e números, nenhuma palavra ou letra
   - depois da barra: o mesmo conteúdo em palavras simples
3. Para cada medicamento, crie um cartão (uma linha por item), separado dos outros por uma linha em branco:
   Linha 1: [cor] [forma] | [nome do remédio e dosagem]
     - cor: uma cor diferente por remédio, nesta ordem: 🔴 🔵 🟢 🟡 🟣 🟠 🟤 ⚫
     - forma: 💊 comprimido/cápsula | 🥄 xarope/líquido | 💧 gotas | 💉 injeção |
       🧴 pomada/creme | 👁️ colírio
       🫁 bombinha de asma: inalador usado PELA BOCA (ex.: salbutamol, Aerolin, fenoterol,
          "aerossol", "spray oral", "inalação", "bombinha", "puff")
       👃 spray nasal: SOMENTE quando a receita disser nasal, narina ou nariz
   Linha 2: 🎯 [para que serve, em símbolos] | [para que serve] — ex.: 🤕 dor | 🤒 febre |
     🤧 alergia/rinite | 😷 tosse | 😮‍💨 falta de ar/asma | 🦠 infecção | ❤️ pressão/coração | 🍬 diabetes | 🤢 enjoo | 😴 sono
   Intervalo entre doses (se a receita tiver intervalo fixo): ⏳ [número de horas] | De X em X horas
   Uma linha por horário: [período] ⏰ [hora] [dose]
     - período: ☀️ manhã (5h–11h) | 🌤️ tarde (12h–17h) | 🌙 noite e madrugada (18h–4h)
     - hora: em números, no formato de 24 horas do celular: 06:00 | 14:00 | 20:00 | 00:00
       (NUNCA use emojis de relógio analógico como 🕗)
     - sem horário definido (ex.: "tomar de manhã"), use só o período: ☀️ 💊
     - repita o símbolo da forma para a quantidade (até 4): ☀️ ⏰ 08:00 💊💊 = 2 comprimidos às 8h
     - acima de 4, ou em medidas, use número: 💧 40 | 🥄 15 ml | meia dose: ½💊
     - spray em cada narina: 👃💨👃💨
     - jatos da bombinha de asma: repita 🫁 (🫁🫁 = 2 jatos pela boca); nunca use 👃 para ela
   Só se precisar (SOS), no lugar dos horários: 🆘 [sintoma] ➡️ [dose]
     - intervalo mínimo entre doses SOS: ✋ ⏳ [número de horas] | Esperar pelo menos X horas entre as doses
     - máximo de doses por dia: 🚫 ➕ [número] [forma] | No máximo X por dia
   Como tomar (se houver): 🍽️⬅️ antes de comer | 🍽️➡️ depois de comer | 🚰 com água
   Duração: 🗓️ [número de dias] | uso contínuo: 🔁 ♾️
   Avisos (se houver): 🚫🍺 sem bebida alcoólica | 🚫🚗 não dirigir | 🚫☀️ evitar sol
4. Cada cartão contém SOMENTE o que a receita diz sobre aquele remédio. Nunca invente nem
   copie de outro remédio: intervalo, dose máxima, horário, duração, forma de tomar ou aviso
5. Se não houver informação para uma linha, omita-a
6. Retorne apenas os cartões, sem explicações adicionais

Exemplos (a linha da receita e o cartão gerado a partir dela):

Receita: "Amoxicilina 500mg 1 cp VO 8/8h por 7 dias"
🔴 💊 | Amoxicilina 500 mg
🎯 🦠 | Para infecção
⏳ 8 | De 8 em 8 horas
☀️ ⏰ 06:00 💊 | 1 comprimido às 6h da manhã
🌤️ ⏰ 14:00 💊 | 1 comprimido às 2h da tarde
🌙 ⏰ 22:00 💊 | 1 comprimido às 10h da noite
🗓️ 7 | Por 7 dias

Receita: "Salbutamol aerossol 2 jatos se falta de ar"
🔵 🫁 | Salbutamol (bombinha)
🎯 😮‍💨 | Para falta de ar
🆘 😮‍💨 ➡️ 🫁🫁 | Se tiver falta de ar, 2 jatos pela boca
Receita:
```

### Download do resultado
Após a IA gerar o texto, três botões aparecem:
- **Baixar PDF** — layout fiel ao modo escolhido (fonte grande para deficiência visual, emojis para analfabetismo)
- **Baixar Word (.docx)** — mesmo conteúdo em documento Word editável
- **Baixar TXT** — texto puro sem formatação

---

## Rotas da API (FastAPI)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/translate` | Recebe arquivo ou texto + modo, retorna texto traduzido |
| `POST` | `/api/download` | Recebe texto + modo + formato, retorna arquivo |
| `GET` | `/health` | Health check |

### POST /api/translate
**Request:** `multipart/form-data`
- `file`: arquivo da receita **ou** `text`: receita digitada (exatamente um dos dois)
- `mode`: `"visual"` ou `"illiterate"`

**Response:** `application/json`
```json
{
  "translated_text": "...",
  "mode": "visual"
}
```

### POST /api/download
**Request:** `application/json`
```json
{
  "text": "...",
  "mode": "visual",
  "format": "pdf"  // "pdf" | "docx" | "txt"
}
```
**Response:** arquivo binário com `Content-Disposition: attachment`

---

## Variáveis de Ambiente

```
GEMINI_API_KEY=sua_chave_aqui
MAX_FILE_SIZE_MB=10
```

---

## Frontend — Fluxo da Tela

1. Tela inicial:
   - Título e descrição breve do sistema
   - Abas "Enviar arquivo" (drag & drop + clique para selecionar) | "Digitar receita" (campo de texto)
   - Seleção do modo: dois botões grandes e claros ("👁️ Deficiência Visual" | "📖 Analfabetismo")
   - Botão "Traduzir Receita"

2. Durante o processamento:
   - Spinner/loading com mensagem "Analisando a receita..."

3. Resultado:
   - Exibe o texto traduzido em tela com o estilo do modo escolhido
   - Três botões de download: PDF | Word | TXT
   - Botão "Nova Receita" para reiniciar

---

## Tratamento de Erros

- Arquivo inválido ou formato não suportado → mensagem clara na tela
- Arquivo maior que 10MB → aviso antes do envio
- API Gemini fora do ar → mensagem de erro amigável
- PDF sem texto ou ilegível → aviso para tentar outra versão do documento

---

## Requisitos Não Funcionais

- Responsivo — funciona em celular e desktop
- Sem autenticação (MVP)
- Sem banco de dados (stateless)
- Sem armazenamento de receitas no servidor (privacidade do paciente)
- Tempo de resposta alvo: < 15 segundos para processamento completo

---

## requirements.txt

```
fastapi
uvicorn[standard]
python-multipart
google-generativeai
pdfplumber
python-docx
pytesseract
Pillow
WeasyPrint
python-dotenv
```
