# Cria a aba "Projeção" no CYREMod_2T26.xlsx (04/10/2026): projeção 2027-31 do deck (slides 58-60) em fórmulas vivas,
# linkadas à aba CYRE. Quatro cenários de lançamento (motor repetido), caixa operacional, DRE, DuPont, valuation (FCFE a Ke, g)
# e grade de sensibilidade. Azul = premissa (input); verde = link à CYRE; preto = fórmula. Rodar: powershell -File modelo_projecao.ps1
# Linhas da CYRE resolvidas pelo rótulo da coluna A em tempo de execução (a planilha ganhou 2 linhas a partir da 137 entre 17/09 e 23/09).
# Diferenças metodológicas vs o deck (documentadas na aba): janela das premissas em % da receita = 1T23-2T26 sem dupla contagem
# (o deck somava 2023+2024+2025+LTM, contando 3T25-4T25 duas vezes); "outras receitas/despesas" pela CYRE (ex não recorrentes:
# o deck incluía o ganho da venda de Cury de 3T25); ações ex-tesouraria da CYRE (linha 99) em vez do capital total.
$ErrorActionPreference = 'Stop'
$path = 'D:\rlavourinha\Pictures\OneDrive\Área de Trabalho\JGP\RLavourinha\2. Homebuilders\1. Modelos\Cyrela\CYREMod_2T26.xlsx'
$xl = New-Object -ComObject Excel.Application; $xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.AskToUpdateLinks = $false
$wb = $xl.Workbooks.Open($path, 0, $false)
$cy = $wb.Worksheets.Item('CYRE')
# ---------------- linhas da CYRE pelo rótulo
$labs = $cy.Range($cy.Cells.Item(1, 1), $cy.Cells.Item(400, 1)).Value2
function RowOf($pattern, $after) { if (-not $after) { $after = 0 }; for ($i = $after + 1; $i -le 400; $i++) { $t = $labs[$i, 1]; if ($t -and ([string]$t) -match $pattern) { return $i } }; throw ('rotulo nao encontrado na CYRE: ' + $pattern) }
$RW = @{}
$RW.rec = RowOf '^Net Operating Revenue'; $RW.gp = RowOf '^Gross Profit$'; $RW.jur = RowOf '^Juros Apropriados no Custo'
$RW.mcmv = RowOf '^MCMV 2 e 3' (RowOf '^Economia de Custos')
$RW.sell = RowOf '^Selling expenses'; $RW.ga = RowOf '^General and administrative'; $RW.oth = RowOf '^Other Operating Revenues'; $RW.eq = RowOf '^Equity Income'
$RW.fin = RowOf '^Resultado Financeiro \[reportado\]'; $RW.ir = RowOf '^Income tax and social contribution'; $RW.min = RowOf '^Minority Shareholders'
$RW.ni = RowOf '^Net Income$'; $RW.roe = RowOf '^ROE LTM'; $RW.nsh = RowOf '^# Ações totais ex-Tesouraria'; $RW.eps = RowOf '^EPS$'
$bs = RowOf '^Balance Sheet'; $ac = RowOf '^Ativo Circulante' $bs; $anc = RowOf '^Ativo Não Circulante' $bs; $pc = RowOf '^Passivo Circulante' $bs; $pnc = RowOf '^Passivo Não Circulante' $bs
$RW.cash = RowOf '^Caixa / TVMs' $ac; $RW.crcp = RowOf '^Contas a Receber$' $ac; $RW.aplp = RowOf '^Aplicações Financeiras \| Longo Prazo' $anc; $RW.crlp = RowOf '^Contas a Receber$' $anc
$RW.empcp = RowOf '^Empréstimos / CRIs' $pc; $RW.emplp = RowOf '^Empréstimos / CRIs' $pnc; $RW.pl = RowOf '^Patrimônio Líquido$' $pnc
$RW.obra = RowOf '^Imóveis em Construção' $bs; $RW.pronto = RowOf '^Imóveis Prontos' $bs; $RW.adi = RowOf '^Adiantamentos de Clientes \[total\]' $bs
$RW.tp = RowOf '^Contas a Pagar por Aquisição de Imóveis \| Terrenos a Pagar' $bs; $RW.terr = RowOf '^Terrenos a custo' $bs; $RW.lanc = RowOf '^Lançamentos 100% \| com permuta' $bs
$old = $null; try { $old = $wb.Worksheets.Item('Projeção') } catch {}
if ($old) { $old.Delete() }
$ws = $wb.Worksheets.Add([Type]::Missing, $cy); $ws.Name = 'Projeção'
$ws.Cells.Font.Name = 'Calibri'; $ws.Cells.Font.Size = 8
$BLUE = 16711680; $GREEN = 32768; $BLACK = 0; $GREY = 8421504
$NUM = '#,##0;(#,##0);-'; $PCT = '0.0%'; $R2 = '0.00'; $DIAS = '0'

function CL($c) { $s = ''; while ($c -gt 0) { $m = ($c - 1) % 26; $s = [string][char](65 + $m) + $s; $c = [math]::Floor(($c - 1) / 26) }; $s }
function Put($r, $c, $v, $kind, $fmt) {
    $cell = $ws.Cells.Item($r, $c)
    if ($v -is [int] -or $v -is [long] -or $v -is [decimal]) { $v = [double]$v }
    try {
        if ($v -is [string] -and $v.StartsWith('=')) { $cell.Formula = $v }
        elseif ($v -is [double]) { $cell.Formula = $v.ToString('R', [Globalization.CultureInfo]::InvariantCulture) }   # Value2 numérico falha via late binding neste arquivo; Formula aceita o número em en-US
        else { $cell.Value2 = $v }
    } catch { throw ('Put falhou em linha {0} coluna {1} com [{2}]: {3}' -f $r, $c, $v, $_.Exception.Message) }
    switch ($kind) { 'in' { $cell.Font.Color = $BLUE } 'link' { $cell.Font.Color = $GREEN } 'note' { $cell.Font.Color = $GREY; $cell.Font.Italic = $true } 'hdr' { $cell.Font.Bold = $true } 'bold' { $cell.Font.Bold = $true } default { $cell.Font.Color = $BLACK } }
    if ($fmt) { $cell.NumberFormat = $fmt }
}
function PutR($r, $c1, $c2, $f, $kind, $fmt) {   # fórmula relativa aplicada a um intervalo (Excel ajusta as referências)
    $rg = $ws.Range($ws.Cells.Item($r, $c1), $ws.Cells.Item($r, $c2))
    try { $rg.Formula = $f } catch { throw ('PutR falhou em linha {0} colunas {1}-{2} com [{3}]: {4}' -f $r, $c1, $c2, $f, $_.Exception.Message) }
    switch ($kind) { 'in' { $rg.Font.Color = $BLUE } 'link' { $rg.Font.Color = $GREEN } default { $rg.Font.Color = $BLACK } }
    if ($fmt) { $rg.NumberFormat = $fmt }
}
function Lab($r, $a, $b, $kind) { Put $r 1 $a $kind $null; if ($b) { Put $r 2 $b 'note' $null } }
# colunas: D=2022 E=2023 F=2024 G=2025 H=LTM 2T26 (proxy 2026) I..M=2027E..2031E; N = soma 1T23-2T26 (só no bloco DFC)
# CYRE: anuais 2022=CJ 2023=CO 2024=CT 2025=CY; LTM = CW+CX+CZ+DA; fins de período 4T22=CI 4T23=CN 4T24=CS 4T25=CX 2T25=CV 2T26=DA
$AN = @{4 = 'CJ'; 5 = 'CO'; 6 = 'CT'; 7 = 'CY'}; $ST = @{4 = 'CI'; 5 = 'CN'; 6 = 'CS'; 7 = 'CX'; 8 = 'DA'}; $ST0 = @{5 = 'CI'; 6 = 'CN'; 7 = 'CS'; 8 = 'CV'}
function Flow($n) { $o = @{}; foreach ($c in 4..7) { $o[$c] = ('=CYRE!{0}{1}' -f $AN[$c], $n) }; $o[8] = ('=CYRE!CW{0}+CYRE!CX{0}+CYRE!CZ{0}+CYRE!DA{0}' -f $n); $o }
function Flow2($n, $m, $sign) { $o = @{}; foreach ($c in 4..7) { $o[$c] = ('=CYRE!{0}{1}{3}CYRE!{0}{2}' -f $AN[$c], $n, $m, $sign) }; $o[8] = ('=(CYRE!CW{0}+CYRE!CX{0}+CYRE!CZ{0}+CYRE!DA{0}){2}(CYRE!CW{1}+CYRE!CX{1}+CYRE!CZ{1}+CYRE!DA{1})' -f $n, $m, $sign); $o }
function Stock($n, $m) { $o = @{}; foreach ($c in 4..8) { if ($m) { $o[$c] = ('=CYRE!{0}{1}+CYRE!{0}{2}' -f $ST[$c], $n, $m) } else { $o[$c] = ('=CYRE!{0}{1}' -f $ST[$c], $n) } }; $o }
function Delta($n, $m) { $o = @{}; foreach ($c in 5..8) { if ($m) { $o[$c] = ('=(CYRE!{0}{2}+CYRE!{0}{3})-(CYRE!{1}{2}+CYRE!{1}{3})' -f $ST[$c], $ST0[$c], $n, $m) } else { $o[$c] = ('=CYRE!{0}{2}-CYRE!{1}{2}' -f $ST[$c], $ST0[$c], $n) } }; $o }
function S14($n) { '(SUM(CYRE!CK{0}:CN{0})+SUM(CYRE!CP{0}:CS{0})+SUM(CYRE!CU{0}:CX{0})+SUM(CYRE!CZ{0}:DA{0}))' -f $n }
function LTM($n) { '(CYRE!CW{0}+CYRE!CX{0}+CYRE!CZ{0}+CYRE!DA{0})' -f $n }
function PutHist($r, $h, $fmt) { foreach ($c in $h.Keys) { Put $r $c $h[$c] 'link' $fmt } }
$CR2 = ('(CYRE!DA{0}+CYRE!DA{1})' -f $RW.crcp, $RW.crlp); $RECL = LTM $RW.rec

# ---------------- cabeçalho
Put 1 1 'Projeção 2027-31 · Cyrela (R$ mi) · cenários de lançamento, caixa operacional, DRE, DuPont e valuation' 'hdr' $null; $ws.Cells.Item(1, 1).Font.Size = 11
Put 2 1 'Modelo do deck de 24-25/09/26 (slides 58-60), em fórmulas. Histórico pela aba CYRE (links em verde, linhas achadas pelo rótulo); linhas da DFC sem correspondente na CYRE pela planilha de DFs do RI (Economatica). Premissas em azul. Permuta: terrenos = 0 (o saldo a pagar rola). Criado em 04/10/2026.' 'note' $null
Put 3 1 'Receita do ano = FREC × Σ pesos × lançamentos t−1..t−4 (ciclo de 39 meses). Recebível: Vivaz a 160 dias, resto nos dias implícitos; mix da Vivaz na receita com a mesma defasagem. Estoque de obra = β × média de 3 anos de lançamentos. Caixa = lucro bruto + Δ capital de giro + linhas em % da receita. FCFE = caixa operacional; VPL a Ke, perpetuidade sobre 2031, menos dívida líquida de 2T26.' 'note' $null
Put 4 1 'ano (auxiliar)' 'note' $null
$years = @{4 = 2022; 5 = 2023; 6 = 2024; 7 = 2025; 8 = 2026; 9 = 2027; 10 = 2028; 11 = 2029; 12 = 2030; 13 = 2031}
foreach ($c in $years.Keys) { Put 4 $c $years[$c] 'note' '0' }
Put 5 1 'R$ mi' 'hdr' $null; Put 5 2 'premissa / fonte' 'hdr' $null
$hd = @{4 = '2022'; 5 = '2023'; 6 = '2024'; 7 = '2025'; 8 = 'LTM 2T26'; 9 = '2027E'; 10 = '2028E'; 11 = '2029E'; 12 = '2030E'; 13 = '2031E'; 14 = 'Σ 1T23-2T26'}
foreach ($c in $hd.Keys) { Put 5 $c $hd[$c] 'hdr' $null; $ws.Cells.Item(5, $c).HorizontalAlignment = -4152 }
Put 6 1 'coluna da CYRE' 'note' $null; foreach ($c in 4..7) { Put 6 $c $AN[$c] 'note' $null }; Put 6 8 'CW+CX+CZ+DA' 'note' $null
$ws.Range('A5:N5').Borders.Item(9).LineStyle = 1

# ---------------- premissas (valor na coluna D)
$P = @{}; $r = 15; Put $r 1 'Premissas' 'hdr' $null; $r++
$P.g = $r;      Lab $r 'crescimento dos lançamentos, a.a.' 'cenários 1, 2 e 4: +5% a.a.; cenário 3: L* em 2027 e +5% depois'; Put $r 4 0.05 'in' $PCT; $r++
$P.w1 = $r;     Lab $r 'peso da receita: lançamentos de t−1' 'ciclo de 39 meses: 15/35/35/15'; Put $r 4 0.15 'in' $PCT; $r++
$P.w2 = $r;     Lab $r 'peso: t−2' $null; Put $r 4 0.35 'in' $PCT; $r++
$P.w3 = $r;     Lab $r 'peso: t−3' $null; Put $r 4 0.35 'in' $PCT; $r++
$P.w4 = $r;     Lab $r 'peso: t−4' $null; Put $r 4 0.15 'in' $PCT; $r++
$P.frec = $r;   Lab $r 'FREC: receita LTM ÷ lançamentos defasados (regra acima)' '0,81 no LTM (vendas de 2025-26 mais lentas); 2020-25 a razão foi ~1,0'; $r++
$P.beta = $r;   Lab $r 'β: estoque de obra a custo 2T26 ÷ média 2024-26 de lançamentos' ('nota de estoque dos ITR (CYRE {0}+{1}) × lançamentos 100% (CYRE {2}); 0,25-0,30 em 2021-26' -f $RW.obra, $RW.pronto, $RW.lanc); $r++
$P.dv = $r;     Lab $r 'dias de recebível da Vivaz (projeção)' 'Cury roda 134-162 dias (CVM, 2021-26)'; Put $r 4 160 'in' $DIAS; $r++
$P.dcury = $r;  Lab $r 'dias de recebível da Cury em 2T26 (observado)' 'CVM: CR ÷ receita 12 m × 365 (usado só para inferir os dias do resto)'; Put $r 4 161.838 'in' '0.0'; $r++
$P.sh = $r;     Lab $r 'participação da Vivaz na receita LTM' ('CYRE {0} ÷ {1} (nota de segmentos)' -f $RW.mcmv, $RW.rec); $r++
$P.dias = $r;   Lab $r 'dias de recebível da Cyrela em 2T26' ('CR (CYRE {0}+{1}) ÷ receita LTM × 365' -f $RW.crcp, $RW.crlp); $r++
$P.dmap = $r;   Lab $r 'dias implícitos do resto (MAP)' '(CR − Vivaz × dias da Cury) ÷ receita do resto'; $r++
$P.vso = $r;    Lab $r 'VSO 12 m em 2T26: vendas ÷ (estoque inicial + lançamentos), VGV 100%' 'planilha operacional do RI: vendas 13,28 bi; estoque 2T25 + lançamentos'; Put $r 4 0.437588 'in' $PCT; $r++
$P.est = $r;    Lab $r 'estoque a valor de mercado em 2T26, VGV 100%' 'planilha operacional do RI'; Put $r 4 17181.2 'in' $NUM; $r++
$P.lstar = $r;  Lab $r 'L*: lançar o que vende = VSO × estoque ÷ (1 − VSO)' 'nível de lançamento que mantém o estoque à VSO atual'; $r++
$P.dpp = $r;    Lab $r 'Vivaz: +p.p. no mix de lançamentos (cenário 4)' $null; Put $r 4 0.30 'in' $PCT; $r++
$P.torre = $r;  Lab $r 'torre Pininfarina: reclassificada de estoque p/ imobilizado em 4T25, sem caixa' 'DFP 2025, nota de imobilizado: sai da Δ obra e dos investimentos (2025 e LTM)'; Put $r 4 431.016 'in' $NUM; $r++
$P.ke = $r;     Lab $r 'Ke' 'premissa'; Put $r 4 0.17 'in' $PCT; $r++
$P.gp = $r;     Lab $r 'g da perpetuidade' $null; Put $r 4 0.04 'in' $PCT; $r++
$P.px = $r;     Lab $r 'preço CYRE3' 'fechamento de 18/09/2026 (B3); trocar pelo add-in JGPSeriesStatic se quiser ao vivo'; Put $r 4 26.67 'in' $R2; $r++
$P.nsh = $r;    Lab $r 'ações ex-tesouraria, mi (ON + PN especiais)' ('CYRE {0}, 2T26 (o deck usou 453,4 mi = capital total com tesouraria)' -f $RW.nsh); Put $r 4 ('=CYRE!DA{0}' -f $RW.nsh) 'link' '#,##0.0'; $r++
$P.dl = $r;     Lab $r 'dívida líquida 2T26 (inclui carteira CashMe como caixa)' ('CYRE {0}+{1} − {2} − {3}' -f $RW.empcp, $RW.emplp, $RW.cash, $RW.aplp); Put $r 4 ('=CYRE!DA{0}+CYRE!DA{1}-CYRE!DA{2}-CYRE!DA{3}' -f $RW.empcp, $RW.emplp, $RW.cash, $RW.aplp) 'link' $NUM; $r++
$P.pl0 = $r;    Lab $r 'PL dos controladores 2T26' ('CYRE {0}' -f $RW.pl); Put $r 4 ('=CYRE!DA{0}' -f $RW.pl) 'link' $NUM; $r++
Put $r 1 'Linhas em % da receita · janela 1T23-2T26 (14 trimestres; o deck usava 2023+2024+2025+LTM, com 3T25-4T25 contados duas vezes)' 'hdr' $null; $r++
$P.rec14 = $r;  Lab $r 'receita líquida 1T23-2T26' ('CYRE {0}' -f $RW.rec); Put $r 4 ('=' + (S14 $RW.rec)) 'link' $NUM; $r++
$P.plb = $r;    Lab $r 'lucro bruto reportado (Gross Profit − juros apropriados)' ('CYRE {0} − {1}' -f $RW.gp, $RW.jur); Put $r 4 ('=(' + (S14 $RW.gp) + '-' + (S14 $RW.jur) + ')/$D$' + $P.rec14) 'link' $PCT; $r++
$P.psga = $r;   Lab $r 'despesas comerciais e administrativas' ('CYRE {0} + {1}' -f $RW.sell, $RW.ga); Put $r 4 ('=(' + (S14 $RW.sell) + '+' + (S14 $RW.ga) + ')/$D$' + $P.rec14) 'link' $PCT; $r++
$P.pir = $r;    Lab $r 'IR/CS (corrente + diferido)' ('CYRE {0}' -f $RW.ir); Put $r 4 ('=' + (S14 $RW.ir) + '/$D$' + $P.rec14) 'link' $PCT; $r++
$P.pfin = $r;   Lab $r 'resultado financeiro (DRE, reportado)' ('CYRE {0}' -f $RW.fin); Put $r 4 ('=' + (S14 $RW.fin) + '/$D$' + $P.rec14) 'link' $PCT; $r++
$P.pout = $r;   Lab $r 'outras receitas/despesas operacionais' ('CYRE {0} (ex não recorrentes; o deck usava a DRE do RI, com o ganho da venda de Cury em 3T25: +0,4% em vez de −0,5%)' -f $RW.oth); Put $r 4 ('=' + (S14 $RW.oth) + '/$D$' + $P.rec14) 'link' $PCT; $r++
$P.peq = $r;    Lab $r 'equivalência patrimonial (Cury, Lavvi, P&P, SPEs)' ('CYRE {0}' -f $RW.eq); Put $r 4 ('=' + (S14 $RW.eq) + '/$D$' + $P.rec14) 'link' $PCT; $r++
$P.pmin = $r;   Lab $r 'minoritários (DRE)' ('CYRE {0}' -f $RW.min); Put $r 4 ('=' + (S14 $RW.min) + '/$D$' + $P.rec14) 'link' $PCT; $r++
$P.pad = $r;    Lab $r 'Δ adiantamentos de clientes (permuta): 4T22 → 2T26' ('CYRE {0}' -f $RW.adi); Put $r 4 ('=(CYRE!DA{0}-CYRE!CI{0})/$D${1}' -f $RW.adi, $P.rec14) 'link' $PCT; $r++
Put $r 1 'Linhas da DFC sem correspondente na CYRE (planilha de DFs do RI / Economatica), R$ mi · D = % da receita; E..H = anos; N = Σ 1T23-2T26' 'hdr' $null; $r++
# trimestres 1T23..2T26 (R$ mi): var. monetária + outros itens do fluxo operacional; dividendos recebidos; compra líq. de ativo permanente; caixa de outros financiamentos (minoritários)
$q_fincx = @(11.0, -42.5, -14.2, -169.0, -10.1, -106.1, 11.2, -81.0, 14.1, -86.0, 33.6, -103.2, 51.8, -82.9)
$q_div = @(28.2, 40.4, 75.3, 103.5, 32.7, 65.3, 46.8, 44.0, 131.6, 99.9, 51.8, 281.0, 60.5, 68.4)
$q_inv = @(-46.4, -99.2, -84.8, 89.9, -38.6, -141.4, -87.9, 87.1, -35.7, -16.9, -58.3, -521.5, -79.3, -94.8)
$q_min = @(-15.6, 15.6, -68.5, -29.5, -26.0, 26.0, -78.4, -79.6, -96.7, 96.7, -240.0, -46.6, -50.9, 50.9)
function Y($q, $i0) { ($q[$i0..($i0 + 3)] | Measure-Object -Sum).Sum }
function PutDFC($r, $q) { Put $r 5 (Y $q 0) 'in' $NUM; Put $r 6 (Y $q 4) 'in' $NUM; Put $r 7 (Y $q 8) 'in' $NUM; Put $r 8 (Y $q 10) 'in' $NUM; Put $r 14 (($q | Measure-Object -Sum).Sum) 'in' $NUM }
$P.fincx = $r;  Lab $r 'ajuste caixa do financeiro (var. monetária não caixa + outros itens pagos, DFC)' 'DFC linhas 104 + 118'; PutDFC $r $q_fincx; Put $r 4 ('=N{0}/$D${1}' -f $r, $P.rec14) $null $PCT; $r++
$P.divjv = $r;  Lab $r 'dividendos recebidos das JVs' 'DFC linha 124'; PutDFC $r $q_div; Put $r 4 ('=N{0}/$D${1}' -f $r, $P.rec14) $null $PCT; $r++
$P.inv = $r;    Lab $r 'investimentos: JVs, SPEs e imobilizado (DFC, bruto)' 'DFC linha 120; inclui a torre em 4T25'; PutDFC $r $q_inv; $r++
$P.invt = $r;   Lab $r 'ajuste da torre (+): sem caixa' 'premissa acima; a mesma cifra sai da Δ obra'; Put $r 7 ('=$D$' + $P.torre) $null $NUM; Put $r 8 ('=$D$' + $P.torre) $null $NUM; Put $r 14 ('=$D$' + $P.torre) $null $NUM; Put ($r - 1) 4 ('=(N{0}+N{1})/$D${2}' -f ($r - 1), $r, $P.rec14) $null $PCT; $r++
$P.mincx = $r;  Lab $r 'minoritários e outros financiamentos (DFC)' 'DFC linha 135'; PutDFC $r $q_min; Put $r 4 ('=N{0}/$D${1}' -f $r, $P.rec14) $null $PCT; $r++
# lançamentos
$r++; Put $r 1 'Lançamentos (VGV 100%, com permuta), R$ mi' 'hdr' $null; $r++
$L = @{}; $L.hist = $r; Lab $r 'histórico' ('CYRE {0} (planilha operacional do RI); LTM = 3T25-2T26' -f $RW.lanc); PutHist $r (Flow $RW.lanc) $NUM; $r++
$L.c1 = $r; Lab $r 'cenário 1 · +5% s/ LTM' $null; PutR $r 4 8 ('=D{0}' -f $L.hist) $null $NUM; PutR $r 9 13 ('=$H{0}*(1+$D${1})^(I$4-2026)' -f $r, $P.g) $null $NUM; $r++
$L.c2 = $r; Lab $r 'cenário 2 · +5% s/ 2025' '2027 = 2025 × 1,05²'; PutR $r 4 8 ('=D{0}' -f $L.hist) $null $NUM; PutR $r 9 13 ('=$G{0}*(1+$D${1})^(I$4-2025)' -f $r, $P.g) $null $NUM; $r++
$L.c3 = $r; Lab $r 'cenário 3 · lançar o que vende (L*), depois +5%' $null; PutR $r 4 8 ('=D{0}' -f $L.hist) $null $NUM; Put $r 9 ('=$D$' + $P.lstar) $null $NUM; PutR $r 10 13 ('=I{0}*(1+$D${1})' -f $r, $P.g) $null $NUM; $r++
$L.c4 = $r; Lab $r 'cenário 4 · +5% s/ LTM, Vivaz +30 p.p.' 'mesmos lançamentos do cenário 1, mix diferente'; PutR $r 4 13 ('=D{0}' -f $L.c1) $null $NUM; $r++
$r++; $L.mix = $r; Lab $r 'mix da Vivaz nos lançamentos (participação Cyrela)' 'lista de empreendimentos do RI × %CBR (_mix_stake); 2026 = LTM'; Put $r 4 0.0822 'in' $PCT; Put $r 5 0.1508 'in' $PCT; Put $r 6 0.2444 'in' $PCT; Put $r 7 0.2820 'in' $PCT; Put $r 8 0.3247 'in' $PCT; $r++
$L.mix13 = $r; Lab $r 'mix · cenários 1-3 (mantém o LTM)' $null; PutR $r 4 8 ('=D{0}' -f $L.mix) $null $PCT; PutR $r 9 13 ('=$H${0}' -f $L.mix) $null $PCT; $r++
$L.mix4 = $r; Lab $r 'mix · cenário 4 (LTM + p.p.)' $null; PutR $r 4 8 ('=D{0}' -f $L.mix) $null $PCT; PutR $r 9 13 ('=$H${0}+$D${1}' -f $L.mix, $P.dpp) $null $PCT; $r++
# premissas derivadas (dependem das linhas acima)
Put $P.frec 4 ('=' + $RECL + ('/($D${0}*G{4}+$D${1}*F{4}+$D${2}*E{4}+$D${3}*D{4})' -f $P.w1, $P.w2, $P.w3, $P.w4, $L.hist)) $null $R2
Put $P.beta 4 ('=(CYRE!DA{0}+CYRE!DA{1})/AVERAGE(F{2}:H{2})' -f $RW.obra, $RW.pronto, $L.hist) $null $R2
Put $P.sh 4 ('=' + (LTM $RW.mcmv) + '/' + $RECL) 'link' $PCT
Put $P.dias 4 ('=' + $CR2 + '/' + $RECL + '*365') 'link' '0.0'
Put $P.dmap 4 ('=365*(' + $CR2 + ('-$D${0}*' -f $P.sh) + $RECL + ('*$D${0}/365)/((1-$D${1})*' -f $P.dcury, $P.sh) + $RECL + ')') $null '0.0'
Put $P.lstar 4 ('=$D${0}*$D${1}/(1-$D${0})' -f $P.vso, $P.est) $null $NUM

# ---------------- motor por cenário
$BR = @{}   # linhas-chave de cada bloco
function Block($R, $k, $name, $pathRow, $mixRow) {
    $B = @{}
    Put $R 1 ('Cenário {0} · {1}' -f $k, $name) 'hdr' $null; $ws.Range($ws.Cells.Item($R, 1), $ws.Cells.Item($R, 14)).Interior.Color = 15921906
    $B.lanc = $R + 1;  Lab $B.lanc 'lançamentos, VGV 100%' 'bloco acima'; PutR $B.lanc 4 13 ('=D{0}' -f $pathRow) $null $NUM
    $B.rec = $R + 2;   Lab $B.rec 'receita líquida' ('hist.: CYRE {0}; proj.: FREC × Σ pesos × lançamentos t−1..t−4' -f $RW.rec); PutHist $B.rec (Flow $RW.rec) $NUM; PutR $B.rec 9 13 ('=$D${0}*($D${1}*H{5}+$D${2}*G{5}+$D${3}*F{5}+$D${4}*E{5})' -f $P.frec, $P.w1, $P.w2, $P.w3, $P.w4, $B.lanc) $null $NUM
    $B.sh = $R + 3;    Lab $B.sh 'participação da Vivaz na receita' 'mix dos lançamentos com a mesma defasagem'; Put $B.sh 8 ('=$D$' + $P.sh) $null $PCT; PutR $B.sh 9 13 ('=$D${0}*H{4}+$D${1}*G{4}+$D${2}*F{4}+$D${3}*E{4}' -f $P.w1, $P.w2, $P.w3, $P.w4, $mixRow) $null $PCT
    $B.dias = $R + 4;  Lab $B.dias 'dias de recebível' 'Vivaz × dias Vivaz + resto × dias implícitos'; Put $B.dias 8 ('=$D$' + $P.dias) $null '0.0'; PutR $B.dias 9 13 ('=I{0}*$D${1}+(1-I{0})*$D${2}' -f $B.sh, $P.dv, $P.dmap) $null '0.0'
    $B.cr = $R + 5;    Lab $B.cr 'contas a receber (fim)' ('hist.: CYRE {0} + {1}; proj.: receita × dias ÷ 365' -f $RW.crcp, $RW.crlp); PutHist $B.cr (Stock $RW.crcp $RW.crlp) $NUM; PutR $B.cr 9 13 ('=I{0}*I{1}/365' -f $B.rec, $B.dias) $null $NUM
    $B.est = $R + 6;   Lab $B.est 'estoque de obra a custo (em construção + pronto, fim)' ('hist.: CYRE {0} + {1}; proj.: β × média 3 anos de lançamentos' -f $RW.obra, $RW.pronto); PutHist $B.est (Stock $RW.obra $RW.pronto) $NUM; PutR $B.est 9 13 ('=$D${0}*AVERAGE(G{1}:I{1})' -f $P.beta, $B.lanc) $null $NUM
    Put ($R + 7) 1 'Do lucro bruto ao caixa' 'bold' $null
    $B.lb = $R + 8;    Lab $B.lb 'lucro bruto (reportado)' ('hist.: CYRE {0} − {1}; proj.: % da receita' -f $RW.gp, $RW.jur); PutHist $B.lb (Flow2 $RW.gp $RW.jur '-') $NUM; PutR $B.lb 9 13 ('=$D${0}*I{1}' -f $P.plb, $B.rec) $null $NUM
    $B.dcr = $R + 9;   Lab $B.dcr 'Δ contas a receber' '−(fim − início)'; PutR $B.dcr 5 7 ('=-(E{0}-D{0})' -f $B.cr) $null $NUM; Put $B.dcr 8 ('=-(H{0}-(CYRE!CV{1}+CYRE!CV{2}))' -f $B.cr, $RW.crcp, $RW.crlp) $null $NUM; PutR $B.dcr 9 13 ('=-(I{0}-H{0})' -f $B.cr) $null $NUM
    $B.dest = $R + 10; Lab $B.dest 'Δ estoque de obra' '−(fim − início); 2025 e LTM sem a torre'; PutR $B.dest 5 6 ('=-(E{0}-D{0})' -f $B.est) $null $NUM; Put $B.dest 7 ('=-(G{0}-F{0})-$D${1}' -f $B.est, $P.torre) $null $NUM; Put $B.dest 8 ('=-(H{0}-(CYRE!CV{1}+CYRE!CV{2}))-$D${3}' -f $B.est, $RW.obra, $RW.pronto, $P.torre) $null $NUM; PutR $B.dest 9 13 ('=-(I{0}-H{0})' -f $B.est) $null $NUM
    $B.terr = $R + 11; Lab $B.terr 'terrenos: −(Δ a custo − Δ a pagar)' ('hist.: CYRE {0} e {1}; proj.: permuta, saldo a pagar rola (0)' -f $RW.terr, $RW.tp)
    $dT = Delta $RW.terr $null; $dP = Delta $RW.tp $null
    foreach ($c in 5..8) { Put $B.terr $c ('=-((' + $dT[$c].Substring(1) + ')-(' + $dP[$c].Substring(1) + '))') 'link' $NUM }
    foreach ($c in 9..13) { Put $B.terr $c 0 'in' $NUM }
    $B.dad = $R + 12;  Lab $B.dad 'Δ adiantamentos de clientes (permuta)' ('hist.: CYRE {0}; proj.: % da receita' -f $RW.adi); $dA = Delta $RW.adi $null; foreach ($c in 5..8) { Put $B.dad $c $dA[$c] 'link' $NUM }; PutR $B.dad 9 13 ('=$D${0}*I{1}' -f $P.pad, $B.rec) $null $NUM
    $B.sga = $R + 13;  Lab $B.sga 'despesas comerciais e administrativas' ('CYRE {0} + {1}' -f $RW.sell, $RW.ga); PutHist $B.sga (Flow2 $RW.sell $RW.ga '+') $NUM; PutR $B.sga 9 13 ('=$D${0}*I{1}' -f $P.psga, $B.rec) $null $NUM
    $B.ir = $R + 14;   Lab $B.ir 'IR/CS' ('CYRE {0}' -f $RW.ir); PutHist $B.ir (Flow $RW.ir) $NUM; PutR $B.ir 9 13 ('=$D${0}*I{1}' -f $P.pir, $B.rec) $null $NUM
    $B.fin = $R + 15;  Lab $B.fin 'resultado financeiro (DRE)' ('CYRE {0}' -f $RW.fin); PutHist $B.fin (Flow $RW.fin) $NUM; PutR $B.fin 9 13 ('=$D${0}*I{1}' -f $P.pfin, $B.rec) $null $NUM
    $B.fincx = $R + 16; Lab $B.fincx 'ajuste caixa do financeiro' 'bloco DFC'; PutR $B.fincx 5 8 ('=E{0}' -f $P.fincx) $null $NUM; PutR $B.fincx 9 13 ('=$D${0}*I{1}' -f $P.fincx, $B.rec) $null $NUM
    $B.out = $R + 17;  Lab $B.out 'outras receitas/despesas' ('CYRE {0}' -f $RW.oth); PutHist $B.out (Flow $RW.oth) $NUM; PutR $B.out 9 13 ('=$D${0}*I{1}' -f $P.pout, $B.rec) $null $NUM
    $B.div = $R + 18;  Lab $B.div 'dividendos recebidos das JVs' 'bloco DFC'; PutR $B.div 5 8 ('=E{0}' -f $P.divjv) $null $NUM; PutR $B.div 9 13 ('=$D${0}*I{1}' -f $P.divjv, $B.rec) $null $NUM
    $B.inv = $R + 19;  Lab $B.inv 'investimentos: JVs, SPEs e imobilizado' 'bloco DFC, sem a torre'; PutR $B.inv 5 8 ('=E{0}+E{1}' -f $P.inv, $P.invt) $null $NUM; PutR $B.inv 9 13 ('=$D${0}*I{1}' -f $P.inv, $B.rec) $null $NUM
    $B.min = $R + 20;  Lab $B.min 'minoritários e outros financiamentos' 'bloco DFC'; PutR $B.min 5 8 ('=E{0}' -f $P.mincx) $null $NUM; PutR $B.min 9 13 ('=$D${0}*I{1}' -f $P.mincx, $B.rec) $null $NUM
    $B.cx = $R + 21;   Lab $B.cx 'caixa operacional (soma; hist.: reconciliado; proj.: FCFE)' $null 'bold'; PutR $B.cx 5 13 ('=SUM(E{0}:E{1})' -f $B.lb, $B.min) $null $NUM; $ws.Range($ws.Cells.Item($B.cx, 1), $ws.Cells.Item($B.cx, 13)).Font.Bold = $true
    $B.rel = $R + 22;  Lab $B.rel 'memo: geração de caixa operacional (release)' 'releases, linha operacional ex-participações'; Put $B.rel 5 -184 'in' $NUM; Put $B.rel 6 52 'in' $NUM; Put $B.rel 7 -191 'in' $NUM; Put $B.rel 8 540 'in' $NUM
    $B.outr = $R + 23; Lab $B.outr 'memo: outros = release − reconciliado' $null; PutR $B.outr 5 8 ('=E{0}-E{1}' -f $B.rel, $B.cx) $null $NUM
    Put ($R + 24) 1 'DRE' 'bold' $null
    $B.eq = $R + 25;   Lab $B.eq 'equivalência patrimonial' ('CYRE {0}' -f $RW.eq); PutHist $B.eq (Flow $RW.eq) $NUM; PutR $B.eq 9 13 ('=$D${0}*I{1}' -f $P.peq, $B.rec) $null $NUM
    $B.mind = $R + 26; Lab $B.mind 'minoritários (DRE)' ('CYRE {0}' -f $RW.min); PutHist $B.mind (Flow $RW.min) $NUM; PutR $B.mind 9 13 ('=$D${0}*I{1}' -f $P.pmin, $B.rec) $null $NUM
    $B.ll = $R + 27;   Lab $B.ll 'lucro líquido' 'lucro bruto + SG&A + outras + financeiro + equivalência + IR + minoritários' 'bold'; PutR $B.ll 4 13 ('=D{0}+D{1}+D{2}+D{3}+D{4}+D{5}+D{6}' -f $B.lb, $B.sga, $B.out, $B.fin, $B.eq, $B.ir, $B.mind) $null $NUM; $ws.Range($ws.Cells.Item($B.ll, 1), $ws.Cells.Item($B.ll, 13)).Font.Bold = $true
    $B.llcy = $R + 28; Lab $B.llcy ('memo: Net Income da CYRE (linha {0})' -f $RW.ni) 'check: deve bater com a linha acima no histórico'; PutHist $B.llcy (Flow $RW.ni) $NUM
    $B.lpa = $R + 29;  Lab $B.lpa 'lucro por ação, R$' $null; PutR $B.lpa 5 13 ('=E{0}/$D${1}' -f $B.ll, $P.nsh) $null $R2
    $B.pe = $R + 30;   Lab $B.pe 'P/L ao preço da premissa' $null; PutR $B.pe 5 13 ('=$D${0}/E{1}' -f $P.px, $B.lpa) $null '0.0"x"'
    Put ($R + 31) 1 'DuPont (PL cresce pelo lucro retido; a companhia distribui o caixa que gera)' 'bold' $null
    $B.pl = $R + 32;   Lab $B.pl 'PL dos controladores (fim)' ('hist.: CYRE {0}' -f $RW.pl); PutHist $B.pl (Stock $RW.pl $null) $NUM; PutR $B.pl 9 13 ('=H{0}+I{1}-MAX(I{2},0)' -f $B.pl, $B.ll, $B.cx) $null $NUM
    $B.plm = $R + 33;  Lab $B.plm 'PL médio' $null; PutR $B.plm 5 7 ('=AVERAGE(D{0}:E{0})' -f $B.pl) $null $NUM; Put $B.plm 8 ('=AVERAGE(CYRE!CV{0},CYRE!DA{0})' -f $RW.pl) 'link' $NUM; PutR $B.plm 9 13 ('=AVERAGE(H{0}:I{0})' -f $B.pl) $null $NUM
    $B.roe = $R + 34;  Lab $B.roe 'ROE: lucro ÷ PL médio' $null 'bold'; PutR $B.roe 5 13 ('=E{0}/E{1}' -f $B.ll, $B.plm) $null $PCT; $ws.Range($ws.Cells.Item($B.roe, 1), $ws.Cells.Item($B.roe, 13)).Font.Bold = $true
    $B.mg = $R + 35;   Lab $B.mg 'margem líquida' $null; PutR $B.mg 5 13 ('=E{0}/E{1}' -f $B.ll, $B.rec) $null $PCT
    $B.giro = $R + 36; Lab $B.giro 'receita ÷ PL médio, x' $null; PutR $B.giro 5 13 ('=E{0}/E{1}' -f $B.rec, $B.plm) $null $R2
    $B.dist = $R + 37; Lab $B.dist 'distribuído (= caixa, se positivo)' $null; PutR $B.dist 9 13 ('=MAX(I{0},0)' -f $B.cx) $null $NUM
    $B
}
$r++; $R0 = $r
$BR[1] = Block $R0 1 '+5% s/ LTM' $L.c1 $L.mix13
$BR[2] = Block ($R0 + 39) 2 '+5% s/ 2025' $L.c2 $L.mix13
$BR[3] = Block ($R0 + 78) 3 'lançar o que vende (L*), depois +5%' $L.c3 $L.mix13
$BR[4] = Block ($R0 + 117) 4 '+5% s/ LTM, Vivaz +30 p.p.' $L.c4 $L.mix4
$r = $R0 + 157

# ---------------- valuation
Put $r 1 'Valuation · FCFE = caixa operacional 2027-31 + perpetuidade sobre 2031 (Ke e g das premissas) − dívida líquida 2T26' 'hdr' $null; $r++
$vh = @{1 = 'cenário'; 9 = '2027E'; 10 = '2028E'; 11 = '2029E'; 12 = '2030E'; 13 = '2031E'; 14 = 'VP 27-31'; 15 = 'VP perpet.'; 16 = '− dív. líq.'; 17 = 'equity'; 18 = 'R$/ação'; 19 = 'vs preço'; 20 = 'P/L 2027'; 21 = 'ROE 2031'; 22 = 'Σ caixa 27-31'}
foreach ($c in $vh.Keys) { Put $r $c $vh[$c] 'hdr' $null; if ($c -gt 1) { $ws.Cells.Item($r, $c).HorizontalAlignment = -4152 } }
$ws.Range($ws.Cells.Item($r, 1), $ws.Cells.Item($r, 22)).Borders.Item(9).LineStyle = 1; $r++
$V = @{}; $names = @{1 = '1 · +5% s/ LTM'; 2 = '2 · +5% s/ 2025'; 3 = '3 · lançar o que vende (L*)'; 4 = '4 · +5% s/ LTM, Vivaz +30 p.p.'}
foreach ($k in 1..4) {
    $B = $BR[$k]; $V[$k] = $r; Put $r 1 $names[$k] $null $null
    PutR $r 9 13 ('=I{0}' -f $B.cx) $null $NUM
    Put $r 14 ('=SUMPRODUCT(I{0}:M{0},1/(1+$D${1})^($I$4:$M$4-2026))' -f $r, $P.ke) $null $NUM
    Put $r 15 ('=M{0}*(1+$D${2})/($D${1}-$D${2})/(1+$D${1})^5' -f $r, $P.ke, $P.gp) $null $NUM
    Put $r 16 ('=-$D${0}' -f $P.dl) $null $NUM
    Put $r 17 ('=N{0}+O{0}+P{0}' -f $r) $null $NUM
    Put $r 18 ('=Q{0}/$D${1}' -f $r, $P.nsh) 'bold' $R2
    Put $r 19 ('=R{0}/$D${1}-1' -f $r, $P.px) $null $PCT
    Put $r 20 ('=I{0}' -f $B.pe) $null '0.0"x"'
    Put $r 21 ('=M{0}' -f $B.roe) $null $PCT
    Put $r 22 ('=SUM(I{0}:M{0})' -f $r) $null $NUM
    $r++
}
$r++; Put $r 1 'Sensibilidade · R$/ação do cenário 1: Ke (linhas) × g da perpetuidade (colunas)' 'hdr' $null; $r++
$gs = @(0.02, 0.03, 0.04, 0.05, 0.06); $kes = @(0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20)
$sg = $r; Put $r 4 'Ke \ g' 'hdr' $null; for ($j = 0; $j -lt 5; $j++) { Put $r (5 + $j) $gs[$j] 'in' $PCT }; $r++
$v1 = $V[1]
foreach ($ke in $kes) {
    Put $r 4 $ke 'in' $PCT
    for ($j = 0; $j -lt 5; $j++) {
        $cc = CL (5 + $j)
        Put $r (5 + $j) ('=(SUMPRODUCT($I${0}:$M${0},1/(1+$D{1})^($I$4:$M$4-2026))+$M${0}*(1+{2}${3})/($D{1}-{2}${3})/(1+$D{1})^5-$D${4})/$D${5}' -f $v1, $r, $cc, $sg, $P.dl, $P.nsh) $null $R2
    }
    $r++
}
$ws.Cells.Item($sg + 4, 7).Font.Bold = $true   # Ke 17% × g 4% (caso base)
Put ($r) 1 'Leitura: a 17% e 4% o VPL fica abaixo do preço em todos os cenários; o preço de tela corresponde a Ke ~14% com g 4%. Perpetuidade ~70% do valor.' 'note' $null; $r++

# ---------------- resumo (linhas 8-14)
Put 8 1 'Resumo por cenário' 'hdr' $null
$rh = @{4 = 'lanç. 2027'; 5 = 'receita 2029'; 6 = 'lucro líq. 2029'; 7 = 'caixa 2029'; 8 = 'Σ caixa 27-31'; 9 = 'R$/ação'; 10 = 'vs preço'; 11 = 'P/L 2027'; 12 = 'ROE 2031'; 13 = 'dias receb. 2031'}
foreach ($c in $rh.Keys) { Put 8 $c $rh[$c] 'hdr' $null; $ws.Cells.Item(8, $c).HorizontalAlignment = -4152 }
$ws.Range('A8:N8').Borders.Item(9).LineStyle = 1
foreach ($k in 1..4) {
    $rr = 8 + $k; $B = $BR[$k]; Put $rr 1 $names[$k] $null $null
    Put $rr 4 ('=I{0}' -f $B.lanc) $null $NUM; Put $rr 5 ('=K{0}' -f $B.rec) $null $NUM; Put $rr 6 ('=K{0}' -f $B.ll) $null $NUM; Put $rr 7 ('=K{0}' -f $B.cx) $null $NUM
    Put $rr 8 ('=V{0}' -f $V[$k]) $null $NUM; Put $rr 9 ('=R{0}' -f $V[$k]) 'bold' $R2; Put $rr 10 ('=S{0}' -f $V[$k]) $null $PCT; Put $rr 11 ('=T{0}' -f $V[$k]) $null '0.0"x"'; Put $rr 12 ('=M{0}' -f $B.roe) $null $PCT; Put $rr 13 ('=M{0}' -f $B.dias) $null '0'
}
Put 13 1 'memo: deck de 25/09/26, cenário 1 (janela 2023+24+25+LTM; outras com o ganho de Cury; 453,4 mi ações)' 'note' $null
Put 13 4 17826 'in' $NUM; Put 13 5 14463 'in' $NUM; Put 13 6 2743 'in' $NUM; Put 13 7 1702 'in' $NUM; Put 13 9 19.34 'in' $R2; Put 13 10 -0.275 'in' $PCT; Put 13 11 5.2 'in' '0.0"x"'; Put 13 12 0.170 'in' $PCT
Put 14 1 ('cenário 1 → colunas 2027E-2031E da aba CYRE (linhas {0}, {1}, {2}, {3}, {4}, {5}, {6})' -f $RW.rec, $RW.ni, $RW.roe, $RW.nsh, $RW.eps, $RW.pl, $RW.lanc) 'note' $null

# ---------------- formato geral
$ws.Columns.Item(1).ColumnWidth = 58; $ws.Columns.Item(2).ColumnWidth = 60; $ws.Columns.Item(3).ColumnWidth = 2
foreach ($c in 4..22) { $ws.Columns.Item($c).ColumnWidth = 10 }
$ws.Columns.Item(2).Font.Color = $GREY; $ws.Columns.Item(2).Font.Italic = $true; $ws.Columns.Item(2).WrapText = $false
$ws.Activate(); $xl.ActiveWindow.FreezePanes = $false; [void]$ws.Range('D7').Select(); $xl.ActiveWindow.FreezePanes = $true; $xl.ActiveWindow.Zoom = 100
[void]$ws.Range('A1').Select()

# ---------------- CYRE: colunas 2027E-2031E (DE..DI) linkadas ao cenário 1
$B = $BR[1]
foreach ($i in 0..4) {
    $c = 109 + $i; $y = 2027 + $i; $col = CL (9 + $i)
    $cy.Cells.Item(1, $c).Value2 = ('{0}E' -f $y); $cy.Cells.Item(1, $c).Font.Bold = $true; $cy.Cells.Item(2, $c).Formula = [string]$y
    foreach ($pair in @(@($RW.rec, $B.rec), @($RW.ni, $B.ll), @($RW.roe, $B.roe), @($RW.nsh, $null), @($RW.eps, $B.lpa), @($RW.pl, $B.pl), @($RW.lanc, $B.lanc))) {
        $cell = $cy.Cells.Item($pair[0], $c)
        if ($pair[0] -eq $RW.nsh) { $cell.Formula = ('=Projeção!$D${0}' -f $P.nsh) } else { $cell.Formula = ('=Projeção!{0}{1}' -f $col, $pair[1]) }
        $cell.Font.Color = $GREEN; $cell.NumberFormat = $cy.Cells.Item($pair[0], 105).NumberFormat
    }
}
$h = $cy.Cells.Item(1, 109); if ($h.Comment) { $h.Comment.Delete() }; [void]$h.AddComment('Projecao 2027-31 (aba Projecao, cenario 1: +5% s/ LTM, permuta): receita, lucro liquido, ROE, acoes, LPA, PL e lancamentos. Criado em 04/10/2026.')

$xl.Calculate()
# ---------------- âncoras: aborta sem salvar se o histórico não bater
function V($r, $c) { $x = $ws.Cells.Item($r, $c).Value2; if ($x -is [double]) { $x } else { [double]::NaN } }
$chk = @(@('PL 2T26', (V $P.pl0 4), 11168.04), @('divida liquida 2T26', (V $P.dl 4), 1161.3), @('CR 2T26', (V $BR[1].cr 8), 6524.46), @('estoque obra 2T26', (V $BR[1].est 8), 3961.6), @('lancamentos LTM', (V $L.hist 8), 16977.3), @('receita LTM', (V $BR[1].rec 8), 9869.5), @('lucro bruto LTM', (V $BR[1].lb 8), 3264.6), @('Net Income 2025', (V $BR[1].llcy 7), 1757.1), @('acoes', (V $P.nsh 4), 435.75))
$bad = @(); foreach ($t in $chk) { if ([double]::IsNaN($t[1]) -or [math]::Abs($t[1] - $t[2]) -gt 0.6) { $bad += ('{0}: {1} (esperado {2})' -f $t[0], $t[1], $t[2]) } }
if ($bad.Count) { $wb.Close($false); $xl.Quit(); throw ('ancoras fora, nada salvo: ' + ($bad -join '; ')) }
$wb.Save()
# ---------------- leitura de verificação
$out = @('linhas CYRE: ' + (($RW.GetEnumerator() | Sort-Object Value | ForEach-Object { '{0}={1}' -f $_.Key, $_.Value }) -join ' '))
foreach ($k in 1..4) { $rr = 8 + $k; $out += ('{0}: lanc27={1} rec29={2} ll29={3} cx29={4} soma={5} ps={6} vs={7} pl27={8} roe31={9} dias31={10}' -f $ws.Cells.Item($rr, 1).Text, $ws.Cells.Item($rr, 4).Text, $ws.Cells.Item($rr, 5).Text, $ws.Cells.Item($rr, 6).Text, $ws.Cells.Item($rr, 7).Text, $ws.Cells.Item($rr, 8).Text, $ws.Cells.Item($rr, 9).Text, $ws.Cells.Item($rr, 10).Text, $ws.Cells.Item($rr, 11).Text, $ws.Cells.Item($rr, 12).Text, $ws.Cells.Item($rr, 13).Text) }
$out += ('FREC={0} beta={1} sh={2} dias={3} dmap={4} lstar={5} nsh={6} dl={7} pl0={8}' -f $ws.Cells.Item($P.frec, 4).Text, $ws.Cells.Item($P.beta, 4).Text, $ws.Cells.Item($P.sh, 4).Text, $ws.Cells.Item($P.dias, 4).Text, $ws.Cells.Item($P.dmap, 4).Text, $ws.Cells.Item($P.lstar, 4).Text, $ws.Cells.Item($P.nsh, 4).Text, $ws.Cells.Item($P.dl, 4).Text, $ws.Cells.Item($P.pl0, 4).Text)
$out += ('pct: lb={0} sga={1} ir={2} fin={3} out={4} eq={5} min={6} ad={7} fincx={8} div={9} inv={10} mincx={11}' -f $ws.Cells.Item($P.plb, 4).Text, $ws.Cells.Item($P.psga, 4).Text, $ws.Cells.Item($P.pir, 4).Text, $ws.Cells.Item($P.pfin, 4).Text, $ws.Cells.Item($P.pout, 4).Text, $ws.Cells.Item($P.peq, 4).Text, $ws.Cells.Item($P.pmin, 4).Text, $ws.Cells.Item($P.pad, 4).Text, $ws.Cells.Item($P.fincx, 4).Text, $ws.Cells.Item($P.divjv, 4).Text, $ws.Cells.Item($P.inv, 4).Text, $ws.Cells.Item($P.mincx, 4).Text)
$B = $BR[1]
foreach ($rw in @($B.lanc, $B.rec, $B.sh, $B.dias, $B.cr, $B.est, $B.lb, $B.dcr, $B.dest, $B.terr, $B.dad, $B.sga, $B.ir, $B.fin, $B.fincx, $B.out, $B.div, $B.inv, $B.min, $B.cx, $B.rel, $B.outr, $B.eq, $B.mind, $B.ll, $B.llcy, $B.lpa, $B.pe, $B.pl, $B.plm, $B.roe, $B.mg, $B.giro)) { $s = $ws.Cells.Item($rw, 1).Text.PadRight(46).Substring(0, 46) + ' |'; foreach ($c in 5..13) { $s += ' ' + $ws.Cells.Item($rw, $c).Text.PadLeft(8) }; $out += $s }
$out += 'valuation:'; foreach ($k in 1..4) { $s = $ws.Cells.Item($V[$k], 1).Text.PadRight(30) + ' |'; foreach ($c in 14..22) { $s += ' ' + $ws.Cells.Item($V[$k], $c).Text.PadLeft(8) }; $out += $s }
$out += 'sens:'; for ($i = 0; $i -le 7; $i++) { $s = ''; foreach ($c in 4..9) { $s += ' ' + $ws.Cells.Item($sg + $i, $c).Text.PadLeft(8) }; $out += $s }
$out += ('CYRE DE{0}={1} DE{2}={3} DI{4}={5} DE{6}={7}' -f $RW.rec, $cy.Cells.Item($RW.rec, 109).Text, $RW.ni, $cy.Cells.Item($RW.ni, 109).Text, $RW.pl, $cy.Cells.Item($RW.pl, 113).Text, $RW.lanc, $cy.Cells.Item($RW.lanc, 109).Text)
$errs = 0; $ur = $ws.UsedRange; foreach ($cell in $ur.Cells) { if ($cell.Text -match '^#') { $errs++; if ($errs -le 12) { $out += ('ERRO {0}: {1}' -f $cell.Address(), $cell.Text) } } }
$out += ('celulas com erro: {0}' -f $errs)
$wb.Close($true); $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
$out -join "`n"
