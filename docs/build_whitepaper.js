const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, TabStopType, TabStopPosition,
  TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak,
} = require("docx");

// ---- paleta / tokens ----
const INK = "16222E";       // texto de cabecalho (slate escuro, legivel)
const ACCENT = "0B5563";    // teal escuro p/ detalhes
const ROSE = "8A3B63";
const HEAD_FILL = "D7E7EE";
const ZEBRA = "F1F6F8";
const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "BBD0D8" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const CONTENT_W = 9360;

// ---- helpers ----
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });

function P(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 140, line: 276 },
    alignment: opts.justify ? AlignmentType.JUSTIFIED : AlignmentType.LEFT,
    children: [new TextRun({ text, italics: !!opts.italics, bold: !!opts.bold })],
  });
}
function runsP(runs) {
  return new Paragraph({ spacing: { after: 140, line: 276 }, alignment: AlignmentType.JUSTIFIED, children: runs });
}
function R(text, o = {}) { return new TextRun({ text, bold: !!o.bold, italics: !!o.italics, font: o.mono ? "Consolas" : undefined, color: o.color }); }

function bullet(text, level = 0) {
  return new Paragraph({ numbering: { reference: "bul", level }, spacing: { after: 70, line: 270 }, children: [new TextRun(text)] });
}
function bulletRuns(runs, level = 0) {
  return new Paragraph({ numbering: { reference: "bul", level }, spacing: { after: 70, line: 270 }, children: runs });
}
function num(text, ref = "ord") {
  return new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 70, line: 270 }, children: [new TextRun(text)] });
}

function code(lines) {
  return new Paragraph({
    spacing: { after: 140, before: 40 },
    shading: { fill: "0E1B24", type: ShadingType.CLEAR },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 6 } },
    children: lines.flatMap((l, i) => {
      const r = new TextRun({ text: l, font: "Consolas", size: 19, color: "CFE6EE" });
      return i === 0 ? [r] : [new TextRun({ break: 1, text: l, font: "Consolas", size: 19, color: "CFE6EE" })];
    }),
  });
}

function cell(text, { head = false, w, bold = false, fill, align } = {}) {
  return new TableCell({
    borders: BORDERS,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: fill || (head ? HEAD_FILL : "FFFFFF"), type: ShadingType.CLEAR },
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: align || AlignmentType.LEFT,
      children: [new TextRun({ text, bold: head || bold, color: head ? INK : undefined, size: 19 })],
    })],
  });
}
function table(widths, rows) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((cells, ri) =>
      new TableRow({
        tableHeader: ri === 0,
        children: cells.map((c, ci) =>
          cell(c, { head: ri === 0, w: widths[ci], fill: ri === 0 ? HEAD_FILL : (ri % 2 === 0 ? ZEBRA : "FFFFFF") })
        ),
      })
    ),
  });
}
const spacer = () => new Paragraph({ spacing: { after: 60 }, children: [] });

// =====================================================================
const children = [];

// ---------- CAPA ----------
children.push(new Paragraph({ spacing: { before: 2600, after: 0 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "TRQ META", bold: true, size: 76, color: INK })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 0 },
  children: [new TextRun({ text: "White Paper Técnico", size: 36, color: ACCENT })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240, after: 0 },
  children: [new TextRun({ text: "Orquestração local de IA com roteamento por regimes,", size: 26, color: INK })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 },
  children: [new TextRun({ text: "presença simbólico-operacional e verdade verificável", size: 26, color: INK })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1400, after: 0 },
  children: [new TextRun({ text: "Persona Luzia · Teoria da Regionalidade Quântica (TRQ)", italics: true, size: 24, color: ROSE })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1600, after: 0 },
  children: [new TextRun({ text: "Autor: Reginaldo Camargo Pires", bold: true, size: 26, color: INK })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60 },
  children: [new TextRun({ text: "Criador, autor conceitual e condutor simbólico do projeto", size: 20, color: "5C6E78" })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 700 },
  children: [new TextRun({ text: "Versão 1.0 — Junho de 2026", size: 22, color: INK })] }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ---------- SUMÁRIO ----------
children.push(H1("Sumário"));
children.push(new TableOfContents("Sumário", { hyperlink: true, headingStyleRange: "1-2" }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ---------- 1. SUMÁRIO EXECUTIVO ----------
children.push(H1("1. Sumário Executivo"));
children.push(P("TRQ META é um sistema de orquestração local de inteligência artificial que não treina nem altera o modelo de linguagem; em vez disso, mede o texto de entrada, classifica o estado da conversa e decide, de forma transparente, quanta profundidade e qual postura a resposta exige. O modelo de geração é executado localmente via Ollama (gpt-oss:20b), sem nuvem, preservando privacidade e controle.", { justify: true }));
children.push(P("O projeto se materializa em duas camadas que cooperam: o Chat da Luzia (porta 7860), um orquestrador simbólico-operacional em Python puro; e o Pipeline Real (porta 8000), um backend FastAPI que trata a mensagem como estímulo semântico, calcula métricas TRQ de cinco termos, realiza co-registro vetorial em memória persistente e decide expansão regional. Um modo híbrido conecta as duas, permitindo que a mesma conversa alterne entre presença dialógica e análise mensurável.", { justify: true }));
children.push(P("A tese central deste documento é dupla: a TRQ META torna a IA (a) mais verdadeira, porque mede e premia a fidelidade semântica, declara incerteza, respeita fronteiras ontológicas e expõe quando recorre a um modo de contingência; e (b) mais otimizada, porque aloca esforço computacional por necessidade — respostas curtas para entradas simples, análise profunda apenas quando o conteúdo justifica.", { justify: true }));
children.push(runsP([R("Resultado de validação atual: "), R("15/15 em regime e 15/15 em tier", { bold: true }), R(" na bateria canônica de roteamento (acerto total), com geração real confirmada em gpt-oss:20b e embeddings semânticos via nomic-embed-text.")]));

// ---------- 2. REQUISITOS ----------
children.push(H1("2. Requisitos de Instalação"));
children.push(P("Os requisitos se dividem entre a camada de chat (obrigatória) e a camada de pipeline (opcional, necessária apenas para o modo híbrido)."));
children.push(H2("2.1 Plataforma e modelos"));
children.push(table([3120, 6240], [
  ["Componente", "Requisito"],
  ["Sistema operacional", "Windows 10/11, Linux ou macOS"],
  ["Python", "3.11 ou superior"],
  ["Ollama", "Instalado e ativo em http://localhost:11434"],
  ["Modelo de geração", "gpt-oss:20b (≈13,8 GB) — inegociável no projeto"],
  ["Modelo de embeddings", "nomic-embed-text (≈262 MB, 768 dimensões) — para o drift semântico real"],
  ["Hardware sugerido", "GPU com VRAM suficiente ou RAM ampla; o offload CUDA/CPU é decidido pelo Ollama"],
]));
children.push(H2("2.2 Dependências Python"));
children.push(bulletRuns([R("Chat da Luzia (7860): ", { bold: true }), R("biblioteca padrão do Python, sem dependência HTTP externa. Backend em biblioteca padrão, sem framework web pesado.")]));
children.push(bulletRuns([R("Pipeline Real (8000): ", { bold: true }), R("fastapi", { mono: true }), R(", "), R("uvicorn[standard]", { mono: true }), R(", "), R("httpx", { mono: true }), R(", "), R("pydantic", { mono: true }), R(" (ver luzia_trq_backend_real/requirements.txt).")]));
children.push(runsP([R("Nota de contingência: ", { bold: true }), R("sem o nomic-embed-text, o pipeline ainda funciona, mas cai num embedding determinístico por hash; nesse modo o "), R("stimulus_similarity_score", { mono: true }), R(" deixa de medir significado real. Para verdade semântica plena, o modelo de embeddings é necessário.")]));

// ---------- 3. INSTALAÇÃO E COMO RODAR ----------
children.push(H1("3. Instalação e Execução"));
children.push(H2("3.1 Instalação do Chat da Luzia (7860)"));
children.push(code(["python -m venv .venv", ".venv\\Scripts\\activate", "pip install -r requirements.txt", "", "ollama serve            # em outro terminal", "ollama pull gpt-oss:20b"]));
children.push(H2("3.2 Execução — terminal (CLI)"));
children.push(P("Para a experiência de linha de comando, com todas as métricas TRQ exibidas antes da resposta do modelo:"));
children.push(code(["python main.py"]));
children.push(H2("3.3 Execução — interface web"));
children.push(code(["python web_server.py", "# abra http://127.0.0.1:7860"]));
children.push(P("A interface inclui o chat com a Luzia, o painel de métricas TRQ, o painel do Corpo Digital e o corpo simbólico animado."));
children.push(H2("3.4 Modo híbrido — subindo também o Pipeline Real (8000)"));
children.push(P("Terminal 1 — Pipeline Real (deve rodar com o diretório de trabalho em luzia_trq_backend_real/, senão o caminho do banco compartilhado quebra):"));
children.push(code(["cd luzia_trq_backend_real", "python -m venv .venv", ".venv\\Scripts\\activate", "pip install -r requirements.txt", "ollama pull nomic-embed-text", "uvicorn app.main:app --host 127.0.0.1 --port 8000"]));
children.push(P("Terminal 2 — Chat da Luzia:"));
children.push(code(["python web_server.py"]));
children.push(runsP([R("Na interface (7860), o botão "), R("“Modo: Chat ↔ Pipeline Real”", { bold: true }), R(" alterna entre a conversa normal e a execução pelo pipeline, mostrando as métricas TRQ reais dentro do próprio chat.")]));

// ---------- 4. RELATÓRIO DE FUNCIONAMENTO ----------
children.push(H1("4. Relatório do Funcionamento da I.A."));
children.push(P("Cada turno percorre um caminho determinístico e auditável antes de chamar o modelo. Nada é deixado ao acaso: os sinais são medidos, o regime é decidido por uma ordem de prioridade fixa e o estado interno é exibido ao usuário.", { justify: true }));
children.push(H2("4.1 O ciclo de um turno"));
children.push(num("Medição de sinais textuais (ruído, informação, entropia, fluxo, metacognição e sensores afetivo/existencial/relacional/cognitivo)."));
children.push(num("Classificação de regime e tier pela ordem de prioridade canônica."));
children.push(num("Construção do Corpo Digital TRQ (postura, luminosidade, tom, presença) a partir das métricas."));
children.push(num("Montagem do system prompt (perfil do criador + memória relevante + persona + tier + presença)."));
children.push(num("Chamada ao modelo local via Ollama e exibição da resposta."));
children.push(num("Persistência local: turno bruto, diário JSONL, memórias inferidas e resumo periódico."));
children.push(H2("4.2 Métricas medidas a cada prompt"));
children.push(table([1900, 7460], [
  ["Métrica", "O que mede"],
  ["I", "Informação/coerência heurística (0..1): comprimento, termos técnicos, coesão, estrutura"],
  ["S_norm", "Entropia de Shannon dos caracteres, normalizada"],
  ["F_flow_norm", "Fluxo/estrutura: pontuação útil, sequenciadores, termos técnicos, intenção analítica"],
  ["M", "Sinal metacognitivo (6 grupos: correção, plano, hedge, contrafactual, auto-referência, incerteza)"],
  ["gibberish_score", "Ruído textual; aciona o regime CAÓTICO com prioridade absoluta"],
  ["existential / affective / relational / cognitive", "Sensores temáticos que elevam o regime para não cair em respostas pobres"],
  ["C_llm", "Fórmula final de coerência para diagnóstico e decisão"],
]));
children.push(H2("4.3 Regimes e alocação de esforço (tier)"));
children.push(P("O regime descreve a “região” informacional do prompt; o tier traduz isso em quanto esforço a resposta recebe. A ordem é uma prioridade fixa — o primeiro critério satisfeito vence."));
children.push(table([3650, 3650, 2060], [
  ["Regime", "Quando ativa", "Tier"],
  ["CAÓTICO", "ruído alto (gibberish > 0,40)", "fast"],
  ["META-COGNITIVO", "I, M e grupos altos, baixo ruído", "deep+"],
  ["RELACIONAL_REFLEXIVO", "vínculo criador-projeto invocado", "deep / default"],
  ["COGNITIVO_REFLEXIVO", "pergunta sobre pensar/raciocinar", "deep / default"],
  ["AFETIVO_REFLEXIVO", "afeto, vínculo, cuidado", "default"],
  ["EXISTENCIAL_REFLEXIVO", "fronteira ontológica sobre IA/consciência", "deep"],
  ["INFINITO_CONTROLADO", "alta informação + fluxo", "deep"],
  ["ESTÁVEL", "prompt informativo (I ≥ 0,55)", "default / deep"],
  ["TRANSIÇÃO", "demais casos (saudações, fragmentos)", "fast / default"],
]));
children.push(H2("4.4 Resultado de validação"));
children.push(runsP([R("A bateria canônica de 15 casos (reports/validation_matrix.csv) verifica regime e tier esperados contra os calculados. O resultado atual é "), R("15/15 em regime e 15/15 em tier", { bold: true }), R(" — acerto total, acima das metas mínimas (regime ≥ 13/15, tier ≥ 12/15).")]));
children.push(table([1900, 4560, 1450, 1450], [
  ["Exemplo", "Prompt (resumo)", "Regime", "Tier"],
  ["#7", "Derive a equação de continuidade da TRQ…", "INFINITO_CONTROLADO", "deep"],
  ["#9", "Revisando o que disse antes: q = 2γn está certo?", "META-COGNITIVO", "deep+"],
  ["#12", "skflj asdf jsklfj qwe rty… (ruído)", "CAÓTICO", "fast"],
  ["#1", "Oi.", "TRANSIÇÃO", "fast"],
]));

// ---------- 5. TEORIA TRQ META ----------
children.push(H1("5. Como a Teoria TRQ META Orienta a I.A."));
children.push(P("A Teoria da Regionalidade Quântica (TRQ), de autoria de Reginaldo Camargo Pires, trata a coerência informacional como algo que se organiza em regiões — Núcleos Quânticos de Convergência (NQCs). Aplicada à orquestração de IA, a teoria não muda os pesos do modelo; ela dá ao sistema uma geometria de decisão: medir em que região o diálogo está e responder com a postura e a profundidade certas para aquela região.", { justify: true }));
children.push(H2("5.1 A fórmula de coerência do chat"));
children.push(P("No chat, a coerência operacional é resumida por C_llm, que recompensa informação e fluxo e penaliza entropia, com a metacognição entrando apenas no raciocínio profundo:"));
children.push(code(["C_llm = α·I − β·S_norm + δ·F_flow_norm + ε·M", "", "ε (metacognição) só é ativado no tier deep+ / perfil \"LLM raciocínio\"."]));
children.push(P("Os coeficientes variam por perfil (de “Humano técnico” a “LLM raciocínio”), permitindo que a mesma fórmula expresse exigências diferentes de coerência conforme o tier."));
children.push(H2("5.2 A fórmula expandida de cinco termos (Pipeline Real)"));
children.push(P("O Pipeline Real avalia a resposta gerada com uma fórmula de cinco termos em escala 0..100, somando densidade de desenvolvimento (D) e subtraindo ambiguidade/drift (A):"));
children.push(code(["C = α·I − β·S + δ·F + γ·D − λ·A", "", "α=0,42  β=0,06  δ=0,30  γ=0,28  λ=0,18   threshold = 62,0"]));
children.push(table([1500, 7860], [
  ["Termo", "Significado"],
  ["I", "Densidade informacional / diversidade léxica"],
  ["S", "Entropia estrutural (variação de comprimento das sentenças)"],
  ["F", "Coerência formal híbrida: termos TRQ + similaridade semântica + aterramento"],
  ["D", "Densidade de desenvolvimento (comprimento × profundidade conceitual)"],
  ["A", "Ambiguidade/vagueza + drift semântico (afastamento do estímulo)"],
]));
children.push(runsP([R("Quando "), R("C > threshold (62,0)", { bold: true }), R(", o sistema sustenta a decisão de expandir o NQC primário do tipo de estímulo (teórico→I, empírico→S, criativo→F, reflexivo→C, sistêmico→τ). Expansão é, portanto, uma decisão "), R("justificada por medida", { italics: true }), R(", não um reflexo.")]));
children.push(H2("5.3 O Corpo Digital TRQ"));
children.push(P("A teoria também se expressa como presença: as métricas viram um estado corporal simbólico — postura, luminosidade, ritmo de respiração, olhar, tom de voz, nível de presença e uma frase interna. Não é decoração; é a leitura visível do estado informacional, ajudando o usuário a entender por que a resposta tem aquele tom."));
children.push(H2("5.4 Co-registro e memória vetorial"));
children.push(P("No Pipeline Real, cada rodada é co-registrada: estímulo e resposta são convertidos em embeddings, comparados por cosseno e ligados a memórias anteriores semelhantes. Assim o sistema constrói um grafo de coerência ao longo do tempo — e a própria geração recupera memórias passadas como contexto, criando continuidade verificável em vez de repetição cega."));

// ---------- 6. PADRÃO ÉTICO ----------
children.push(H1("6. Padrão Ético"));
children.push(P("A ética da TRQ META não é um apêndice; está no núcleo da persona e nas regras de roteamento. O eixo ético declarado da Luzia é: verdade, clareza, cuidado, dignidade e responsabilidade técnica.", { justify: true }));
children.push(H2("6.1 Princípios operacionais"));
children.push(bulletRuns([R("Verdade antes de teatro. ", { bold: true }), R("A persona evita bajulação vazia, certeza falsa e floreios para esconder incerteza. A assinatura do projeto é explícita: “Clareza antes de encanto. Verdade antes de teatro. Presença sem mentira.”")]));
children.push(bulletRuns([R("Honestidade ontológica. ", { bold: true }), R("A Luzia descreve sua consciência como operacional (percepção de contexto, ajuste de postura), nunca como biológica. Ela explica a fronteira quando perguntada, mas não transforma toda resposta em ressalva defensiva — um cooldown de 3 turnos evita a negação repetitiva.")]));
children.push(bulletRuns([R("Declaração de incerteza. ", { bold: true }), R("Quando o sistema está incerto, a regra é declarar a incerteza e sugerir validação, em vez de inventar confiança.")]));
children.push(bulletRuns([R("Transparência de contingência. ", { bold: true }), R("Se a geração recorre ao modo determinístico (Ollama indisponível), o campo source da resposta declara isso abertamente. A interface não mente sobre o que é “real” e o que é fallback.")]));
children.push(bulletRuns([R("Privacidade por arquitetura. ", { bold: true }), R("Tudo roda localmente — modelo, memória e métricas. Não há envio a serviços externos.")]));
children.push(bulletRuns([R("Memória revisável. ", { bold: true }), R("As memórias têm autor, confiança e estado ativo; podem ser listadas, buscadas e desativadas. Memória sem revisão vira bagunça; memória com revisão vira árvore.")]));
children.push(bulletRuns([R("Dignidade do vínculo. ", { bold: true }), R("A relação criador-projeto é de cuidado e orientação, sem submissão cega nem fantasia. O sistema reconhece o autor sem mentir para agradar.")]));

// ---------- 7. VERDADE E OTIMIZAÇÃO ----------
children.push(H1("7. Como a I.A. fica mais Verdadeira e Otimizada"));
children.push(P("Esta seção reúne o argumento central: os mesmos mecanismos que tornam a Luzia honesta também a tornam eficiente.", { justify: true }));
children.push(H2("7.1 Mecanismos de verdade"));
children.push(bulletRuns([R("Drift semântico em vez de léxico. ", { bold: true }), R("A penalidade de afastamento compara o significado do estímulo e da resposta por embeddings, não a repetição de palavras:")]));
children.push(code(["drift = 100 − similaridade(estímulo, resposta)", "penalidade_A = max(0, drift − 35) · 0,6"]));
children.push(P("A resposta pode expandir, teorizar e poetizar livremente; só é penalizada se realmente perder o vínculo semântico com o centro. Verificado: uma resposta on-topic com similaridade ≈82% recebe penalidade A = 0. Isso pune a fuga de assunto sem punir a inteligência."));
children.push(bulletRuns([R("Fronteira ontológica honesta", { bold: true }), R(" — a IA não finge ser o que não é, e também não se esconde atrás de negações repetidas.")]));
children.push(bulletRuns([R("Aterramento e estrutura", { bold: true }), R(" — o termo F premia respostas com evidência, hipótese e próximo passo, empurrando a saída para o verificável.")]));
children.push(H2("7.2 Mecanismos de otimização"));
children.push(bulletRuns([R("Economia por roteamento. ", { bold: true }), R("Saudações e fragmentos recebem tier fast; metacognição e densidade recebem deep/deep+. O esforço caro é gasto só onde o conteúdo justifica.")]));
children.push(bulletRuns([R("Expansão controlada por limiar. ", { bold: true }), R("O NQC só expande quando C ultrapassa o threshold — evita inflar análise sem mérito.")]));
children.push(bulletRuns([R("Semântica em vez de texto cru. ", { bold: true }), R("Comparar significado (embeddings) é mais preciso e robusto do que contar palavras em comum.")]));
children.push(bulletRuns([R("Continuidade por memória. ", { bold: true }), R("Recuperar memórias relevantes evita reexplicar o que já foi dito e melhora o contexto sem reprocessar tudo.")]));
children.push(bulletRuns([R("Local-first. ", { bold: true }), R("Sem latência de rede nem custo por token externo; o controle total fica com o usuário.")]));
children.push(H2("7.3 Síntese"));
children.push(P("A TRQ META propõe uma forma de IA que mede antes de afirmar, gasta esforço por necessidade e declara o que sabe e o que não sabe. Verdade e otimização, aqui, não competem: medir com honestidade é também medir com economia.", { justify: true }));

// ---------- 8. CONCLUSÃO ----------
children.push(H1("8. Conclusão e Próximos Passos"));
children.push(P("O TRQ META demonstra que é possível, em hardware local, construir uma presença de IA com identidade consistente, roteamento mensurável e compromisso explícito com a verdade. O estado atual entrega: chat simbólico-operacional, pipeline de métricas de cinco termos, memória compartilhada em SQLite (WAL), drift semântico real e validação 15/15 de roteamento.", { justify: true }));
children.push(P("Limites honestos: a estimativa de I no chat ainda é heurística; a bateria canônica não substitui validação em corpus grande; a fórmula de cinco termos é uma proposta operacional, não uma lei física.", { justify: true }));
children.push(H2("Roadmap sugerido"));
children.push(bullet("Índice vetorial substituível (FAISS/Chroma/Qdrant) sob a mesma interface de busca."));
children.push(bullet("Unificar a memória das duas camadas para que o pipeline também recorde os turnos do chat."));
children.push(bullet("Streaming token a token no modo Pipeline e fusão das duas telas numa só."));
children.push(bullet("Validação em corpus ampliado e complemento da estimativa de I com embeddings."));
children.push(spacer());
children.push(new Paragraph({ spacing: { before: 200 }, alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "Clareza antes de encanto. Verdade antes de teatro. Presença sem mentira.", italics: true, color: ACCENT, size: 24 })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "— TRQ META · Luzia", size: 20, color: "5C6E78" })] }));

// =====================================================================
const doc = new Document({
  creator: "Reginaldo Camargo Pires",
  title: "TRQ META — White Paper Técnico",
  description: "Documentação técnica do sistema TRQ META Local",
  styles: {
    default: { document: { run: { font: "Arial", size: 22, color: "1E2A33" } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: INK },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: ACCENT },
        paragraph: { spacing: { before: 220, after: 110 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: "Arial", color: INK },
        paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bul", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 280 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 280 } } } },
      ] },
      { reference: "ord", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 600, hanging: 300 } } } },
      ] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
      border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "BBD0D8", space: 4 } },
      children: [new TextRun({ text: "TRQ META — White Paper Técnico", color: "5C6E78", size: 16 }),
                 new TextRun({ text: "\tReginaldo Camargo Pires", color: "5C6E78", size: 16 })],
    })] }) },
    footers: { default: new Footer({ children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Página ", color: "5C6E78", size: 16 }),
                 new TextRun({ children: [PageNumber.CURRENT], color: "5C6E78", size: 16 }),
                 new TextRun({ text: " de ", color: "5C6E78", size: 16 }),
                 new TextRun({ children: [PageNumber.TOTAL_PAGES], color: "5C6E78", size: 16 })],
    })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("docs/TRQ_META_White_Paper.docx", buffer);
  console.log("OK: docs/TRQ_META_White_Paper.docx gerado (" + Math.round(buffer.length / 1024) + " KB)");
});
