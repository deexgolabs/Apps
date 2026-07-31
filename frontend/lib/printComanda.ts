interface ComandaLine {
  label: string
  qty?: number
  unitPrice?: number
  total: number
}

interface ComandaData {
  appName: string
  title: string
  subtitle?: string
  lines: ComandaLine[]
  total: number
  footer?: string
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const money = (value: number) => `R$ ${value.toFixed(2)}`

/**
 * Abre uma janela nova só com o conteúdo da comanda, formatada pra largura de
 * impressora térmica (58/80mm — texto monoespaçado, sem UI do painel), e
 * dispara o print() do navegador direto. Janela separada em vez de CSS
 * @media print na página inteira porque o painel tem months de UI ao redor
 * que não faz sentido tentar esconder com @media print.
 */
export function printComanda(data: ComandaData): void {
  const printWindow = window.open('', '_blank', 'width=380,height=600')
  if (!printWindow) {
    // Pop-up bloqueado pelo navegador -- não há fallback silencioso razoável,
    // quem chama já mostra um toast de erro nesse caso.
    throw new Error('popup-blocked')
  }

  const linesHtml = data.lines
    .map((line) => {
      const qtyPrefix = line.qty ? `${line.qty}x ` : ''
      const unitSuffix = line.unitPrice != null ? ` (${money(line.unitPrice)} cada)` : ''
      return `
        <div class="line">
          <span>${escapeHtml(qtyPrefix + line.label)}${escapeHtml(unitSuffix)}</span>
          <span>${escapeHtml(money(line.total))}</span>
        </div>`
    })
    .join('')

  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(data.title)}</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    width: 280px;
    margin: 0 auto;
    padding: 12px;
    color: #000;
  }
  h1 { font-size: 15px; text-align: center; margin: 0 0 2px; }
  .subtitle { text-align: center; font-size: 12px; margin: 0 0 8px; }
  hr { border: none; border-top: 1px dashed #000; margin: 8px 0; }
  .line { display: flex; justify-content: space-between; gap: 8px; padding: 2px 0; }
  .total { display: flex; justify-content: space-between; font-weight: bold; font-size: 14px; margin-top: 6px; }
  .footer { text-align: center; font-size: 11px; margin-top: 10px; white-space: pre-line; }
  @media print {
    body { width: 100%; }
  }
</style>
</head>
<body>
  <h1>${escapeHtml(data.appName)}</h1>
  <div class="subtitle">${escapeHtml(data.title)}</div>
  ${data.subtitle ? `<div class="subtitle">${escapeHtml(data.subtitle)}</div>` : ''}
  <hr />
  ${linesHtml || '<p>Nenhum item</p>'}
  <hr />
  <div class="total"><span>TOTAL</span><span>${escapeHtml(money(data.total))}</span></div>
  ${data.footer ? `<div class="footer">${escapeHtml(data.footer)}</div>` : ''}
  <script>
    window.onload = function () {
      window.print();
    };
  </script>
</body>
</html>`

  printWindow.document.open()
  printWindow.document.write(html)
  printWindow.document.close()
}
