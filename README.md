# Receita Acessível

Aplicação web que traduz receitas médicas para dois públicos:

- **👁️ Deficiência Visual** — texto sem abreviações, em frases curtas, exibido com fonte grande (32px), alto contraste e espaçamento duplo.
- **📖 Analfabetismo** — um cartão por remédio que o paciente entende só pelas imagens: cor para associar à caixa, forma do remédio, para que serve, horários em números (⏰ 08:00), quantidade e duração. Ao lado de cada linha vai um texto curto para o farmacêutico ou o familiar que ajuda o paciente.

O médico envia a receita (PDF, Word ou TXT) ou digita o texto dela, escolhe o modo, e a IA (Google Gemini) gera a versão acessível. O resultado pode ser baixado em **PDF**, **Word (.docx)** ou **TXT**.

Nenhuma receita é armazenada no servidor: todo o processamento é feito em memória.

## ⚠️ Aviso

Este é um **projeto acadêmico**, não um dispositivo médico.

- O texto é gerado por inteligência artificial e **pode conter erros**. Todo resultado deve ser **conferido por um profissional de saúde** contra a receita original antes de ser entregue a um paciente.
- No plano gratuito da API do Gemini, o Google pode usar o conteúdo enviado para melhorar seus produtos. **Não envie receitas reais** com dados de pacientes nesse plano. Para uso real, utilize o plano pago e observe a LGPD.

## Pré-requisitos

- **Python 3.11+**
- **Chave da API do Gemini** (gratuita, veja abaixo)
- **Tesseract OCR** (opcional) — usado como alternativa quando o Gemini não consegue ler um PDF escaneado.
  - Windows: instalador em <https://github.com/UB-Mannheim/tesseract/wiki> (marque o idioma **Portuguese** durante a instalação) e adicione a pasta de instalação ao `PATH`.
  - Linux: `sudo apt install tesseract-ocr tesseract-ocr-por`
- **Bibliotecas do WeasyPrint** (para gerar PDF) — sem elas, os downloads em Word e TXT continuam funcionando.
  - Windows: instale o [MSYS2](https://www.msys2.org/), rode `pacman -S mingw-w64-x86_64-pango` no terminal do MSYS2 e adicione `WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin` ao `.env`.
  - Linux: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0`
  - Para os emojis aparecerem no PDF, o sistema precisa de uma fonte de emojis (no Windows, a Segoe UI Emoji já vem instalada; no Linux, instale `fonts-noto-color-emoji`).

## Como obter a chave da API do Gemini

1. Acesse <https://aistudio.google.com> e entre com uma conta Google.
2. Clique em **Get API key** → **Create API key**.
3. Copie a chave. Não é necessário cartão de crédito.

## Instalação

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r backend/requirements.txt
```

Copie `.env.example` para `.env` e preencha a chave:

```
GEMINI_API_KEY=sua_chave_aqui
MAX_FILE_SIZE_MB=10
```

Opcionalmente, defina `GEMINI_MODEL` para usar outro modelo (padrão: `gemini-3.1-flash-lite`; o `gemini-3.8-flash` tem cota gratuita de só 20 requisições por dia).

## Como rodar

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Abra <http://localhost:8000> no navegador.

## Publicação (Render)

O projeto tem um `Dockerfile` com tudo de que o servidor precisa: Pango (PDF), fontes e Tesseract.

1. Envie o projeto para um repositório **privado** no GitHub. O `.env` e os PDFs da raiz ficam de fora pelo `.gitignore`.
2. No [Render](https://render.com), crie um **Web Service** a partir do repositório, com runtime **Docker**.
3. Em **Environment**, defina:
   - `GEMINI_API_KEY`: a chave do Gemini;
   - `APP_PASSWORD`: a senha de acesso ao site. Com ela definida, o navegador pede usuário e senha; o usuário pode ser qualquer um.
4. Opcional: em **Health Check Path**, use `/health`, que não pede senha.

Para testar a imagem localmente:

```bash
docker build -t receita-acessivel .
docker run -p 8001:8000 --env-file .env -e APP_PASSWORD=teste receita-acessivel
```

## Símbolos do modo Analfabetismo

Os símbolos permitidos ficam em `backend/symbols.py`, cada um com seu significado. As imagens de cada símbolo ficam em `frontend/emoji/` e vêm de duas fontes (detalhes em `frontend/emoji/NOTICE.txt`):

- [Health Icons](https://healthicons.org) (domínio público, CC0): ícones que mostram pessoas e objetos reais, como uma pessoa tossindo, uma pessoa com febre, o inalador e o medidor de glicose. Ficam listados em `HEALTH_ICONS`, em `symbols.py`.
- [Noto Emoji](https://github.com/googlefonts/noto-emoji) (Apache 2.0, em `frontend/emoji/LICENSE`): todos os demais símbolos.

Para adicionar ou trocar um símbolo, edite `symbols.py` e rode, dentro de `backend/`:

```bash
python fetch_emoji.py
```

## API

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/translate` | `multipart/form-data` com `file` (PDF, DOCX ou TXT) **ou** `text` (receita digitada), e `mode` (`visual` ou `illiterate`). Retorna `{"translated_text", "mode"}`. |
| `POST` | `/api/download` | JSON `{"text", "mode", "format"}` (`pdf`, `docx` ou `txt`). Retorna o arquivo. |
| `GET` | `/health` | Verificação de saúde. |

## Licença

O código está sob a [licença MIT](LICENSE). As imagens em `frontend/emoji/` mantêm as licenças originais: Noto Emoji (Apache 2.0) e Health Icons (domínio público, CC0). Veja `frontend/emoji/NOTICE.txt`.
