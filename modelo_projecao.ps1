# Projeção 2027-31 do cenário base (lançamentos +5% a.a. sobre o LTM 2T26, permuta, Vivaz a 160 dias) escrita DENTRO da aba CYRE
# do CYREMod_2T26.xlsx (versão 2, 04/10/2026, a pedido: sem aba separada, sem cenários). Coluna 2026 (DD) = base: fluxos LTM 2T26 e
# saldos de 2T26; colunas 2027-2031 (DE..DI) = projeção. Premissas moram nas próprias linhas de razão da CYRE (% receita, margens por
# segmento, yoy) e num bloco "Premissas da projeção" no rodapé (lançamentos, defasagem, recebível, estoque, DFC, Ke/g), seguido da
# ponte do lucro bruto ao caixa e do valuation. Azul = premissa; preto = fórmula. Rodar: powershell -File modelo_projecao.ps1
$ErrorActionPreference = 'Stop'
$path = 'D:\rlavourinha\Pictures\OneDrive\Área de Trabalho\JGP\RLavourinha\2. Homebuilders\1. Modelos\Cyrela\CYREMod_2T26.xlsx'
$xl = New-Object -ComObject Excel.Application; $xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.AskToUpdateLinks = $false
$wb = $xl.Workbooks.Open($path, 0, $false)
try { $wb.AutoSaveOn = $false } catch {}   # arquivo no OneDrive: sem AutoSave, para uma execução interrompida não deixar estado parcial
$ws = $wb.Worksheets.Item('CYRE')
# rodapé (731+) é meu: limpa antes de reescrever (execução anterior interrompida pode ter deixado rótulos)
if ($ws.Cells.Item(732, 1).Value2 -and ([string]$ws.Cells.Item(732, 1).Value2) -notmatch '^Premissas da proje') { throw 'linha 732 ocupada por conteudo que nao e meu' }
$ws.Range($ws.Cells.Item(731, 1), $ws.Cells.Item(820, 125)).Clear() | Out-Null
$BLUE = 16711680; $BLACK = 0; $GREY = 8421504
# ---------------- colunas anuais: 2022=CJ 2023=CO 2024=CT 2025=CY 2026(base)=DD 2027..2031=DE..DI; trimestres 2T25=CV 3T25=CW 4T25=CX 1T26=CZ 2T26=DA
$ANN = @('CJ', 'CO', 'CT', 'CY', 'DD', 'DE', 'DF', 'DG', 'DH', 'DI'); $ANNI = @(88, 93, 98, 103, 108, 109, 110, 111, 112, 113)
$PRJ = 5..9; $BASE = 4; $HIST = 1..3
function S14($n) { '(SUM(CK{0}:CN{0})+SUM(CP{0}:CS{0})+SUM(CU{0}:CX{0})+SUM(CZ{0}:DA{0}))' -f $n }   # 1T23-2T26
function LTM($n) { '(CW{0}+CX{0}+CZ{0}+DA{0})' -f $n }
function Tok($pat, $i) { $pat.Replace('{c}', $ANN[$i]).Replace('{p4}', $ANN[$i - 4]).Replace('{p3}', $ANN[$i - 3]).Replace('{p2}', $ANN[$i - 2]).Replace('{p}', $ANN[$i - 1]) }
function Lab($r) { [string]$ws.Cells.Item($r, 1).Value2 }
function Chk($r, $pat) { if ((Lab $r) -notmatch $pat) { throw ('linha {0} nao e "{1}": "{2}"' -f $r, $pat, (Lab $r)) } }
function Cell($r, $ci, $f, $blue) {
    $cell = $ws.Cells.Item($r, $ci)
    if ($f -is [double] -or $f -is [int]) { $cell.Formula = ([double]$f).ToString('R', [Globalization.CultureInfo]::InvariantCulture) } else { try { $cell.Formula = $f } catch { throw ('formula invalida em linha {0} col {1}: {2}' -f $r, $ci, $f) } }
    $cor = 0; if ($blue) { $cor = 16711680 }; $cell.Font.Color = $cor   # (subexpressão $(if…) na atribuição COM dá "Specified cast is not valid")
    $fmt = $ws.Cells.Item($r, 105).NumberFormat; if ($fmt -and $fmt -ne 'General') { $cell.NumberFormat = $fmt }
}
function Proj($r, $pat, $cols, $blue) { foreach ($i in $cols) { Cell $r $ANNI[$i] (Tok $pat $i) $blue } }   # padrão com tokens {c} {p} {p2} {p3} {p4}
function Base($r, $f) { Cell $r 108 $f $false }                                                              # coluna 2026 (base)
function Drv($r, $deFormula) { Cell $r 109 $deFormula $true; Proj $r ('={p}' + $r) (6..9) $true }           # premissa: calibrada em 2027, repetida (editável) até 2031
function Note($r, $ci, $t) { $c = $ws.Cells.Item($r, $ci); if ($c.Comment) { $c.Comment.Delete() }; [void]$c.AddComment($t) }
function Fmt($r, $ci, $f) { $ws.Cells.Item($r, $ci).NumberFormat = $f }

# ---------------- âncoras de linha (aborta se a CYRE mudou)
$L = @{3 = '^Gross Operating Revenue'; 10 = '^Deductions'; 11 = '^% Net Revenues'; 12 = '^ROB \| 12m'; 21 = '^Net Operating Revenue'; 22 = '^yoy'; 24 = '^Alto Padrão'; 25 = '^Médio'; 26 = '^MCMV 2 e 3'; 27 = '^Outros'; 28 = '^Operating Costs'; 29 = '^Juros Apropriados'; 30 = '^Gross Profit$'; 35 = '^Alto Padrão'; 37 = '^Médio'; 39 = '^MCMV 2 e 3'; 41 = '^Outros \| Loteamento'; 42 = '^Margem Bruta'; 44 = '^Selling expenses'; 45 = '^% Net Revenues'; 47 = '^General and administrative'; 48 = '^% Net Revenues'; 49 = '^Other Operating Revenues'; 50 = '^% Net Revenues'; 51 = '^Equity Income'; 52 = '^% Net Revenues'; 53 = '^EBIT$'; 56 = '^EBIT$'; 57 = '^Resultado Financeiro \[ajustado\]'; 59 = '^CashMe$'; 60 ='^Resultado Financeiro \[reportado\]'; 61 = '^Income before taxes'; 62 = '^Income tax'; 63 = '^% Gross Revenues'; 64 = '^Income after taxes'; 65 = '^Minority Shareholders'; 66 = '^% Net Revenues'; 70 = '^Net Income$'; 73 = '^Reported Net Income'; 74 = '^Recurring Net Income'; 76 = '^ROE LTM'; 97 = '^# Ações ex-Treasury'; 99 = '^# Ações totais'; 100 = '^EPS$'; 123 = '^Equivalência Patrimonial'; 173 = '^Ativo Circulante'; 174 = '^Caixa / TVMs'; 175 = '^Contas a Receber$'; 176 = '^Imóveis a Comercializar$'; 179 = '^Ativo Não Circulante'; 181 = '^Contas a Receber$'; 185 = '^Investimentos'; 188 = '^Ativo Total'; 189 = '^Passivo Circulante'; 192 = '^Adiantamentos de Clientes$'; 195 = '^Passivo Não Circulante'; 197 = '^Adiantamentos de Clientes$'; 200 = '^Minoritários'; 201 = '^Patrimônio Líquido$'; 204 = '^Check'; 206 = '^Imóveis a Comercializar \| Estoque'; 207 = '^Imóveis em Construção'; 208 = '^Imóveis Prontos'; 209 = '^Terrenos$'; 211 = '^Encargos Capitalizados'; 212 = '^Provisão para Distratos'; 219 = '^Adiantamentos de Clientes \[total\]'; 222 = '^Contas a Pagar por Aquisição de Imóveis \| Terrenos'; 234 = '^LandBank 100%'; 241 = '^Lançamentos 100% \| com permuta'; 244 = '^MCMV 2 e 3'; 339 = '^Contas a Receber$'; 345 = '^Net Debt$'; 349 = '^Dividendo \(fluxo\)$'; 355 = '^Geração de Caixa$'; 363 = '^Dívida Bruta$'; 373 = '^Dívida Líquida \| Ajustada$'; 395 = '^Lançamentos 100% \| com permuta'; 397 = '^Lançamentos %CYRE'; 549 = '^LandBank 100%'; 552 = '^years of launches'; 669 = '^VGV Lançado \(100%\)'; 671 = '^VGV Lançado \(%CYRE\)'; 699 = '^Receita liquida'; 701 = '^% Margem bruta'; 708 = '^Receita liquida'; 717 = '^Receita liquida'; 724 = '^Retorno op'}
foreach ($k in $L.Keys) { Chk $k $L[$k] }
if ($ws.Cells.Item(730, 1).Value2 -or $ws.Cells.Item(731, 1).Value2) { throw 'linhas 730-731 ocupadas' }

# ---------------- limpeza: aba Projeção, links que eu havia criado (cols 108-120), comentários
$old = $null; try { $old = $wb.Worksheets.Item('Projeção') } catch {}
if ($old) { $old.Delete() }
$fz = $ws.Range($ws.Cells.Item(1, 108), $ws.Cells.Item(730, 120)).Formula; $n = 0
for ($i = 1; $i -le 730; $i++) { for ($j = 1; $j -le 13; $j++) { $f = [string]$fz[$i, $j]; if ($f -match 'Proje' -or $f -eq '=#REF!') { $ws.Cells.Item($i, 107 + $j).ClearContents(); $n++ } } }
foreach ($ci in 109, 116) { $c = $ws.Cells.Item(1, $ci); if ($c.Comment -and $c.Comment.Text() -match 'Projecao') { $c.Comment.Delete() } }
"links apagados: $n"

# ---------------- bloco de premissas no rodapé
$pb = 732; $P = @{}
$ws.Cells.Item($pb, 1).Value2 = 'Premissas da projeção 2027-31 · cenário base: lançamentos +5% a.a. sobre o LTM 2T26, terrenos em permuta, Vivaz a 160 dias de recebível · coluna 2026 = base (fluxos LTM 2T26, saldos 2T26) · 04/10/2026'; $ws.Cells.Item($pb, 1).Font.Bold = $true
$r = $pb + 1
function Row($key, $label) { $script:P[$key] = $script:r; $ws.Cells.Item($script:r, 1).Value2 = $label; $script:r++ }
Row 'g' 'crescimento dos lançamentos, a.a. (premissa por ano)'
Row 'w1' 'receita: peso dos lançamentos de t−1 (ciclo de 39 meses: 15/35/35/15)'
Row 'w2' 'receita: peso de t−2'
Row 'w3' 'receita: peso de t−3'
Row 'w4' 'receita: peso de t−4'
Row 'frec' 'FREC: receita LTM ÷ lançamentos defasados pela regra acima (0,81; 2020-25 ~1,0)'
Row 'beta' 'β: estoque de obra a custo (207+208) ÷ média 2024-26 dos lançamentos 100%'
Row 'dv' 'dias de recebível da Vivaz (premissa; Cury roda 134-162 dias)'
Row 'dcury' 'dias de recebível da Cury em 2T26 (observado, CVM; só para inferir os dias do resto)'
Row 'sh' 'participação da Vivaz (MCMV) na receita: hist. = 26 ÷ 21; proj. = mix dos lançamentos com a defasagem 15/35/35/15'
Row 'dias' 'dias de recebível: hist. = (175+181) ÷ receita × 365; proj. = Vivaz × dias Vivaz + resto × dias implícitos'
Row 'dmap' 'dias implícitos do resto (MAP) em 2T26 = (CR − Vivaz × dias Cury) ÷ receita do resto'
Row 'mix' 'mix da Vivaz nos lançamentos 100% = 244 ÷ 241 (proj.: premissa, mantém o LTM)'
Row 'cr' 'contas a receber total (fim): hist. = 175+181; proj. = receita × dias ÷ 365'
Row 'est' 'estoque de obra a custo (fim): hist. = 207+208; proj. = β × média de 3 anos dos lançamentos'
Row 'jur' 'juros apropriados no custo (29), % da receita · 1T23-2T26'
Row 'pfin' 'resultado financeiro reportado (60), % da receita · 1T23-2T26'
Row 'pfincx' 'ajuste caixa do financeiro (DFC: var. monetária não caixa + outros itens pagos), % da receita · 1T23-2T26: −573 ÷ 28.148'
Row 'pdiv' 'dividendos recebidos das JVs (DFC), % da receita · 1T23-2T26: 1.129 ÷ 28.148'
Row 'pinv' 'investimentos em JVs, SPEs e imobilizado (DFC, ex-torre Pininfarina), % da receita · 1T23-2T26: −697 ÷ 28.148'
Row 'pmin' 'minoritários e outros financiamentos (DFC), % da receita · 1T23-2T26: −543 ÷ 28.148'
Row 'pad' 'Δ adiantamentos de clientes (219), % da receita · 4T22→2T26 ÷ receita 1T23-2T26'
Row 'ke' 'Ke'
Row 'gp' 'g da perpetuidade'
Row 'px' 'preço CYRE3 (célula DO10)'
Row 'nsh' 'ações ex-tesouraria, mi (linha 99)'
Row 'scr' 'CR: parcela circulante (175 ÷ (175+181), 2T26)'
Row 'sest' 'imóveis a comercializar: parcela circulante (176 ÷ 206, 2T26)'
Row 'sobra' 'estoque de obra: em construção ÷ (construção + pronto), 2T26'
Row 'sad' 'adiantamentos de clientes: parcela circulante (192 ÷ 219, 2T26)'
Row 'salto' 'receita: Alto Padrão ÷ (Alto + Médio), LTM'
Row 'sout' 'receita: Outros ÷ total, LTM'
Row 'slanc' 'lançamentos: Alto Padrão ÷ (Alto + Médio), LTM'
Row 'scyre' 'lançamentos %CYRE ÷ 100% (397 ÷ 395), LTM'
$r++; $P.hcx = $r; $ws.Cells.Item($r, 1).Value2 = 'Geração de caixa · do lucro bruto ao caixa (R$ mi) · 2023-25 e base 2026 = histórico reconciliado; 2027-31 = projeção (FCFE)'; $ws.Cells.Item($r, 1).Font.Bold = $true; $r++
Row 'lb' 'lucro bruto reportado (30 − 29)'
Row 'dcr' 'Δ contas a receber: −(fim − início)'
Row 'dest' 'Δ estoque de obra: −(fim − início); 2025 e base sem a torre Pininfarina (R$ 431 mi reclassificados p/ imobilizado em 4T25, sem caixa)'
Row 'terr' 'terrenos: −(Δ a custo 209 − Δ a pagar 222); proj.: permuta, o saldo a pagar rola (0)'
Row 'dad' 'Δ adiantamentos de clientes (219)'
Row 'sga' 'despesas comerciais e administrativas (44 + 47)'
Row 'ir' 'IR/CS (62)'
Row 'fin' 'resultado financeiro reportado (60)'
Row 'fincx' 'ajuste caixa do financeiro (DFC; hist. da planilha de DFs do RI)'
Row 'out' 'outras receitas/despesas (49)'
Row 'div' 'dividendos recebidos das JVs (DFC)'
Row 'inv' 'investimentos: JVs, SPEs e imobilizado (DFC, ex-torre)'
Row 'min' 'minoritários e outros financiamentos (DFC)'
Row 'cx' 'caixa operacional (soma) · hist.: reconciliado; proj.: FCFE'
Row 'rel' 'memo: geração de caixa operacional do release'
Row 'dist' 'distribuído aos acionistas (= caixa, se positivo) → PL cresce pelo lucro retido'
Row 'roe' 'ROE: lucro líquido ÷ PL médio'
$r++; $P.hv = $r; $ws.Cells.Item($r, 1).Value2 = 'Valuation · FCFE 2027-31 + perpetuidade sobre 2031, a Ke e g acima, menos dívida líquida de 2T26'; $ws.Cells.Item($r, 1).Font.Bold = $true; $r++
Row 'fcfe' 'FCFE = caixa operacional'
Row 'ano' 'anos de desconto'
Row 'fat' 'fator de desconto'
Row 'vp' 'valor presente'
Row 'svp' 'VP 2027-31'
Row 'tv' 'perpetuidade: FCFE 2031 × (1 + g) ÷ (Ke − g)'
Row 'pvtv' 'VP da perpetuidade'
Row 'dl' 'dívida líquida 2T26 (190 + 196 − 174 − 180; carteira CashMe como caixa)'
Row 'eq' 'equity'
Row 'ps' 'R$ por ação'
Row 'vs' 'VPL ÷ preço − 1'
$ws.Range($ws.Cells.Item($pb, 1), $ws.Cells.Item($r, 113)).Font.Name = 'Calibri'; $ws.Range($ws.Cells.Item($pb, 1), $ws.Cells.Item($r, 113)).Font.Size = 8
$NUM = '#,##0;(#,##0);-'; $PCT = '0.0%'; $R2 = '0.00'
function PutP($key, $i, $f, $blue, $fmt) {
    $ci = $ANNI[$i]; $rr = $P[$key]; if (-not $rr) { throw ('PutP: chave sem linha: ' + $key) }
    $cell = $ws.Cells.Item($rr, $ci)
    $step = 'formula'
    try {
        if ($f -is [double] -or $f -is [int]) { $cell.Formula = ([double]$f).ToString('R', [Globalization.CultureInfo]::InvariantCulture) } else { $cell.Formula = $f }
        $step = 'cor'; $cor = 0; if ($blue) { $cor = 16711680 }; $cell.Font.Color = $cor
        $step = 'formato [' + $fmt + ']'; $cell.NumberFormat = $fmt
    } catch { throw ('PutP falhou em {6}: {0} linha {1} col {2} i={3} [{4}]: {5}' -f $key, $rr, $ci, $i, $f, $_.Exception.Message, $step) }
}
function ProjP($key, $pat, $cols, $blue, $fmt) { foreach ($i in $cols) { PutP $key $i (Tok $pat $i) $blue $fmt } }
# premissas
foreach ($i in $PRJ) { PutP 'g' $i 0.05 $true $PCT }
PutP 'w1' 5 0.15 $true $PCT; PutP 'w2' 5 0.35 $true $PCT; PutP 'w3' 5 0.35 $true $PCT; PutP 'w4' 5 0.15 $true $PCT
$W = '$DE${0}' -f $P.w1; $W2 = '$DE${0}' -f $P.w2; $W3 = '$DE${0}' -f $P.w3; $W4 = '$DE${0}' -f $P.w4
PutP 'frec' $BASE ('=' + (LTM 21) + ('/({0}*CY241+{1}*CT241+{2}*CO241+{3}*CJ241)' -f $W, $W2, $W3, $W4)) $false $R2
PutP 'beta' $BASE '=(DA207+DA208)/((CT241+CY241+DD241)/3)' $false $R2
foreach ($i in $PRJ) { PutP 'dv' $i 160 $true '0' }
PutP 'dcury' $BASE 161.838 $true '0.0'
ProjP 'sh' '={c}26/{c}21' (1..3) $false $PCT; PutP 'sh' $BASE ('=' + (LTM 26) + '/' + (LTM 21)) $false $PCT
ProjP 'sh' ('={0}*{{p}}{1}+{2}*{{p2}}{1}+{3}*{{p3}}{1}+{4}*{{p4}}{1}' -f $W, $P.mix, $W2, $W3, $W4) $PRJ $false $PCT
ProjP 'dias' '=({c}175+{c}181)/{c}21*365' (1..3) $false '0'; PutP 'dias' $BASE '=(DA175+DA181)/DD21*365' $false '0'
ProjP 'dias' ('={{c}}{0}*{{c}}{1}+(1-{{c}}{0})*$DD${2}' -f $P.sh, $P.dv, $P.dmap) $PRJ $false '0'
PutP 'dmap' $BASE ('=365*((DA175+DA181)-DD{0}*DD21*DD{1}/365)/((1-DD{0})*DD21)' -f $P.sh, $P.dcury) $false '0'
ProjP 'mix' '={c}244/{c}241' (0..3) $false $PCT; PutP 'mix' $BASE ('=' + (LTM 244) + '/' + (LTM 241)) $false $PCT; ProjP 'mix' ('=$DD${0}' -f $P.mix) $PRJ $true $PCT
ProjP 'cr' '={c}175+{c}181' (0..3) $false $NUM; PutP 'cr' $BASE '=DA175+DA181' $false $NUM; ProjP 'cr' ('={{c}}21*{{c}}{0}/365' -f $P.dias) $PRJ $false $NUM
ProjP 'est' '={c}207+{c}208' (0..3) $false $NUM; PutP 'est' $BASE '=DA207+DA208' $false $NUM; ProjP 'est' ('=$DD${0}*({{c}}241+{{p}}241+{{p2}}241)/3' -f $P.beta) $PRJ $false $NUM
PutP 'jur' $BASE ('=' + (S14 29) + '/' + (S14 21)) $false $PCT
PutP 'pfin' $BASE ('=' + (S14 60) + '/' + (S14 21)) $false $PCT
PutP 'pfincx' $BASE ('=-573.3/' + (S14 21)) $true $PCT
PutP 'pdiv' $BASE ('=1129.4/' + (S14 21)) $true $PCT
PutP 'pinv' $BASE ('=(-1127.8+431.016)/' + (S14 21)) $true $PCT
PutP 'pmin' $BASE ('=-542.6/' + (S14 21)) $true $PCT
PutP 'pad' $BASE ('=(DA219-CI219)/' + (S14 21)) $false $PCT
foreach ($k in 'jur', 'pfin', 'pfincx', 'pdiv', 'pinv', 'pmin', 'pad') { ProjP $k ('=$DD${0}' -f $P[$k]) $PRJ $true $PCT }
PutP 'ke' $BASE 0.17 $true $PCT; PutP 'gp' $BASE 0.04 $true $PCT; PutP 'px' $BASE '=DO10' $true $R2; PutP 'nsh' $BASE '=DA99' $false '#,##0.0'
PutP 'scr' $BASE '=DA175/(DA175+DA181)' $false $PCT; PutP 'sest' $BASE '=DA176/DA206' $false $PCT; PutP 'sobra' $BASE '=DA207/(DA207+DA208)' $false $PCT; PutP 'sad' $BASE '=DA192/DA219' $false $PCT
PutP 'salto' $BASE ('=' + (LTM 24) + '/(' + (LTM 24) + '+' + (LTM 25) + ')') $false $PCT; PutP 'sout' $BASE ('=' + (LTM 27) + '/' + (LTM 21)) $false $PCT
PutP 'slanc' $BASE ('=' + (LTM 242) + '/(' + (LTM 242) + '+' + (LTM 243) + ')') $false $PCT; PutP 'scyre' $BASE ('=' + (LTM 397) + '/' + (LTM 395)) $false $PCT
$ws.Cells.Item($P.pfincx, 1).Font.Color = $GREY; $ws.Cells.Item($P.pdiv, 1).Font.Color = $GREY; $ws.Cells.Item($P.pinv, 1).Font.Color = $GREY; $ws.Cells.Item($P.pmin, 1).Font.Color = $GREY

# ---------------- DRE (coluna base 2026 = LTM; 2027-31 = projeção)
foreach ($n in 3, 10, 21, 24, 25, 26, 27, 28, 29, 30, 35, 37, 39, 41, 44, 47, 49, 51, 57, 59, 60, 62, 65, 70, 73, 74, 242, 243, 244, 349, 395, 397, 401, 402, 403, 699, 700, 708, 709, 717, 718) { Base $n ('=' + (LTM $n)) }
Base 12 '=DD3'; Base 76 '=DA76'; Base 97 '=DA97'; Base 98 '=DA98'; Base 123 '=DD51'; Base 241 '=DD242+DD243+DD244'
$c1 =$ws.Cells.Item(1, 108); if ($c1.Comment) { $c1.Comment.Delete() }; [void]$c1.AddComment('2026 = base da projecao: fluxos LTM 2T26 (3T25-2T26), saldos de 2T26. 2027-2031: projecao do cenario base; premissas nas linhas de razao (azul) e no bloco do rodape (linha 732+).')
Proj 241 ('={{p}}241*(1+{{c}}{0})' -f $P.g) $PRJ
Proj 244 ('={{c}}{0}*{{c}}241' -f $P.mix) $PRJ; Proj 242 ('=({{c}}241-{{c}}244)*$DD${0}' -f $P.slanc) $PRJ; Proj 243 '={c}241-{c}242-{c}244' $PRJ
Proj 21 ('=$DD${0}*({1}*{{p}}241+{2}*{{p2}}241+{3}*{{p3}}241+{4}*{{p4}}241)' -f $P.frec, $W, $W2, $W3, $W4) $PRJ
Proj 22 '={c}21/{p}21-1' (4..9)
Drv 11 ('=' + (S14 10) + '/' + (S14 3)); Proj 3 '={c}21/(1+{c}11)' $PRJ; Proj 10 '={c}3*{c}11' $PRJ; Proj 11 '={c}10/{c}3' @(4); Proj 12 '={c}3' $PRJ
Proj 26 ('={{c}}{0}*{{c}}21' -f $P.sh) $PRJ; Proj 27 ('=$DD${0}*{{c}}21' -f $P.sout) $PRJ; Proj 24 ('=({{c}}21-{{c}}26-{{c}}27)*$DD${0}' -f $P.salto) $PRJ; Proj 25 '={c}21-{c}24-{c}26-{c}27' $PRJ
Proj 699 '={c}24' $PRJ; Proj 708 '={c}25' $PRJ; Proj 717 '={c}26' $PRJ
Drv 701 ('=' + (S14 700) + '/' + (S14 699)); Drv 710 ('=' + (S14 709) + '/' + (S14 708)); Drv 719 ('=' + (S14 718) + '/' + (S14 717))
Proj 701 '={c}700/{c}699' @(4); Proj 710 '={c}709/{c}708' @(4); Proj 719 '={c}718/{c}717' @(4)
Proj 700 '={c}701*{c}699' $PRJ; Proj 709 '={c}710*{c}708' $PRJ; Proj 718 '={c}719*{c}717' $PRJ
Proj 35 '={c}700' $PRJ; Proj 37 '={c}709' $PRJ; Proj 39 '={c}718' $PRJ
Drv 42 ('=' + (S14 41) + '/' + (S14 27)); Proj 42 '={c}41/{c}27' @(4); Proj 41 '={c}42*{c}27' $PRJ
Proj 29 ('=$DD${0}*{{c}}21' -f $P.jur) $PRJ; Proj 30 '={c}35+{c}37+{c}39+{c}41+{c}29' $PRJ; Proj 28 '={c}30-{c}21' $PRJ
Proj 31 '={c}30/{p}30-1' (4..9); Proj 32 '={c}30/{c}21' (4..9); Proj 33 '=({c}30+{c}88)/({c}21+{c}88)' (4..9); Proj 34 '=({c}21+{c}28-{c}29)/{c}21' (4..9)
Proj 36 '={c}35/{c}24' (4..9); Proj 38 '={c}37/{c}25' (4..9); Proj 40 '={c}39/{c}26' (4..9); Proj 43 '={c}34-({c}35+{c}37+{c}39)/({c}24+{c}25+{c}26)' (4..9)
Drv 45 ('=' + (S14 44) + '/' + (S14 21)); Proj 45 '={c}44/{c}21' @(4); Proj 44 '={c}45*{c}21' $PRJ
Drv 48 ('=' + (S14 47) + '/' + (S14 21)); Proj 48 '={c}47/{c}21' @(4); Proj 47 '={c}48*{c}21' $PRJ
Drv 50 ('=' + (S14 49) + '/' + (S14 21)); Proj 50 '={c}49/{c}21' @(4); Proj 49 '={c}50*{c}21' $PRJ
Drv 52 ('=' + (S14 51) + '/' + (S14 21)); Proj 52 '={c}51/{c}21' @(4); Proj 51 '={c}52*{c}21' $PRJ; Proj 123 '={c}51' $PRJ
Proj 53 '={c}30+{c}44+{c}47+{c}49+{c}51' (4..9); Proj 54 '={c}53/{c}21' (4..9); Proj 55 '={c}53/{p}53-1' (4..9); Proj 56 '={c}53' (4..9)
Proj 60 ('=$DD${0}*{{c}}21' -f $P.pfin) $PRJ; Proj 57 '={c}60-{c}29' $PRJ; Proj 58 '={c}57/AVERAGE({p}345,{c}345)' (4..9); Proj 61 '={c}57+{c}56+N({c}59)' (4..9)   # 57 = reportado − juros apropriados (CashMe não separada na projeção)
Drv 63 ('=' + (S14 62) + '/' + (S14 3)); Proj 63 '={c}62/{c}3' @(4); Proj 62 '={c}63*{c}3' $PRJ; Proj 64 '={c}62+{c}61' (4..9)
Drv 66 ('=' + (S14 65) + '/' + (S14 21)); Proj 66 '={c}65/{c}21' @(4); Proj 65 '={c}66*{c}21' $PRJ; Proj 67 '={c}65/{c}61' (4..9)
Proj 70 '={c}65+{c}64' $PRJ; Proj 71 '={c}70/{c}21' (4..9); Proj 72 '={c}70/{p}70-1' (4..9); Proj 73 '={c}70' $PRJ; Proj 74 '={c}70' $PRJ
Proj 76 '={c}70/AVERAGE({p}201,{c}201)' $PRJ; Proj 97 '={p}97' $PRJ; Proj 98 '={p}98' $PRJ; Proj 99 '=IF({c}97="","",{c}97+N({c}98))' (4..9); Proj 100 '={c}70/{c}97' (4..9)
# ---------------- ponte do lucro bruto ao caixa (2023-25, base 2026 = LTM, 2027-31)
ProjP 'lb' '={c}30-{c}29' (1..9) $false $NUM
ProjP 'dcr' ('=-({{c}}{0}-{{p}}{0})' -f $P.cr) (1..3 + $PRJ) $false $NUM; PutP 'dcr' $BASE '=-((DA175+DA181)-(CV175+CV181))' $false $NUM
ProjP 'dest' ('=-({{c}}{0}-{{p}}{0})' -f $P.est) (1..2 + $PRJ) $false $NUM; PutP 'dest' 3 ('=-(CY{0}-CT{0})-431.016' -f $P.est) $false $NUM; PutP 'dest' $BASE '=-((DA207+DA208)-(CV207+CV208))-431.016' $false $NUM
ProjP 'terr' '=-(({c}209-{p}209)-({c}222-{p}222))' (1..3) $false $NUM; PutP 'terr' $BASE '=-((DA209-CV209)-(DA222-CV222))' $false $NUM; foreach ($i in $PRJ) { PutP 'terr' $i 0 $true $NUM }
ProjP 'dad' '={c}219-{p}219' (1..3) $false $NUM; PutP 'dad' $BASE '=DA219-CV219' $false $NUM; ProjP 'dad' ('={{c}}{0}*{{c}}21' -f $P.pad) $PRJ $false $NUM
ProjP 'sga' '={c}44+{c}47' (1..9) $false $NUM; ProjP 'ir' '={c}62' (1..9) $false $NUM; ProjP 'fin' '={c}60' (1..9) $false $NUM; ProjP 'out' '={c}49' (1..9) $false $NUM
$H = @{fincx = @(-214.7, -186.0, -141.5, -100.7); div = @(247.4, 188.8, 564.3, 461.7); inv = @(-140.5, -180.8, -201.4, -322.9); min = @(-98.0, -158.0, -286.6, -286.6); rel = @(-184, 52, -191, 540)}
foreach ($k in $H.Keys) { for ($j = 0; $j -lt 4; $j++) { PutP $k ($j + 1) $H[$k][$j] $true $NUM } }
ProjP 'fincx' ('={{c}}{0}*{{c}}21' -f $P.pfincx) $PRJ $false $NUM; ProjP 'div' ('={{c}}{0}*{{c}}21' -f $P.pdiv) $PRJ $false $NUM; ProjP 'inv' ('={{c}}{0}*{{c}}21' -f $P.pinv) $PRJ $false $NUM; ProjP 'min' ('={{c}}{0}*{{c}}21' -f $P.pmin) $PRJ $false $NUM
ProjP 'cx' ('=SUM({{c}}{0}:{{c}}{1})' -f $P.lb, $P.min) (1..9) $false $NUM; $ws.Range($ws.Cells.Item($P.cx, 1), $ws.Cells.Item($P.cx, 113)).Font.Bold = $true
ProjP 'dist' ('=MAX({{c}}{0},0)' -f $P.cx) $PRJ $false $NUM
ProjP 'roe' '={c}70/AVERAGE({p}201,{c}201)' (1..3 + $PRJ) $false $PCT; PutP 'roe' $BASE '=DA76' $false $PCT
# ---------------- balanço (base = 2T26; 2027-31 roda com o caixa)
foreach ($n in 174, 175, 176, 177, 178, 180, 181, 182, 183, 185, 186, 187, 190, 191, 192, 193, 194, 196, 197, 198, 199, 200, 201, 207, 208, 209, 210, 211, 212, 218, 234, 364, 366, 367, 368, 372, 375, 550) { Base $n ('=DA' + $n) }
Proj 174 ('={{p}}174+{{c}}{0}-{{c}}{1}' -f $P.cx, $P.dist) $PRJ
Proj 175 ('={{c}}{0}*$DD${1}' -f $P.cr, $P.scr) $PRJ; Proj 181 ('={{c}}{0}-{{c}}175' -f $P.cr) $PRJ
Proj 176 ('={{c}}206*$DD${0}' -f $P.sest) $PRJ; Proj 182 '={c}206-{c}176' $PRJ
foreach ($n in 177, 178, 180, 183, 186, 187, 190, 191, 194, 196, 198, 199, 209, 210, 212, 218, 234, 364, 366, 367, 368, 372, 375, 550) { Proj $n ('={p}' + $n) $PRJ }
Proj 173 '=SUM({c}174:{c}178)' (4..9); Proj 179 '=SUM({c}180:{c}183)' (4..9); Proj 184 '=SUM({c}185:{c}187)' (4..9); Proj 188 '={c}184+{c}179+{c}173' (4..9)
Proj 185 ('={{p}}185+{{c}}51-{{c}}{0}-{{c}}{1}' -f $P.div, $P.inv) $PRJ
Proj 192 ('={{p}}192+{{c}}{0}*$DD${1}' -f $P.dad, $P.sad) $PRJ; Proj 197 ('={{p}}197+{{c}}{0}*(1-$DD${1})' -f $P.dad, $P.sad) $PRJ; Proj 193 '=0' $PRJ
Proj 189 '=SUM({c}190:{c}192,{c}193:{c}194)' (4..9); Proj 195 '=SUM({c}196:{c}199)' (4..9)
Proj 200 ('={{p}}200-{{c}}65+{{c}}{0}' -f $P.min) $PRJ; Proj 201 ('={{p}}201+{{c}}70-{{c}}{0}' -f $P.dist) $PRJ; Proj 202 '={c}201/{p}201-1' (4..9)
Proj 203 '={c}201+{c}200+{c}195+{c}189' (4..9); Proj 204 '=ABS({c}203-{c}188)<5' (4..9)
Proj 207 ('={{c}}{0}*$DD${1}' -f $P.est, $P.sobra) $PRJ; Proj 208 ('={{c}}{0}-{{c}}207' -f $P.est) $PRJ; Proj 211 ('={{p}}211-{{c}}{0}' -f $P.fincx) $PRJ
Proj 206 '=+{c}207+{c}208+{c}209+{c}210+{c}211+{c}212' (4..9); Proj 213 '={c}206-{c}176-{c}182' (4..9)
Proj 215 '={c}218' (4..9); Proj 219 '={c}192+{c}197' (4..9); Proj 220 '=IF({c}219="","",{c}218/{c}219)' (4..9)
Proj 222 '={c}198+{c}191' (4..9); Proj 223 '={c}218' (4..9); Proj 224 '={c}223+{c}222' (4..9); Proj 225 '={c}209' (4..9); Proj 226 '={c}225-{c}224' (4..9); Proj 227 '={c}226/{c}201' (4..9)
Proj 229 '={c}225-{c}222' (4..9); Proj 230 '=1-{c}222/{c}225' (4..9); Proj 231 '={c}222/{c}201' (4..9); Proj 232 '={c}225/{c}234' (4..9)
Proj 339 '=+{c}341+{c}342' (4..9); Proj 341 '={c}175' (4..9); Proj 342 '=+{c}181' (4..9); Proj 340 '={c}339/{c}671*365' (4..9)
Proj 344 '=({c}345-{p}345)+{c}349' $PRJ; Proj 345 '={c}190+{c}196-{c}174' (4..9); Proj 346 '={c}345/{c}201' (4..9)
Proj 349 ('=-{{c}}{0}' -f $P.dist) $PRJ; Proj 350 '={c}349' $PRJ; Proj 351 '=-{c}349/{c}70' (4..9)
Proj 355 '={p}373-{c}373-{c}350' $PRJ; Proj 356 '={c}70' $PRJ; Proj 357 '={c}222-{p}222' $PRJ; Proj 358 '={c}339-{p}339' $PRJ; Proj 359 '={c}219-{p}219' $PRJ
Proj 363 '={c}190+{c}196' (4..9); Proj 365 '={c}363-{c}364' (4..9); Proj 369 '={c}174' (4..9); Proj 370 '={c}180' (4..9); Proj 371 '={c}365-{c}369-{c}370' (4..9); Proj 373 '={c}371+{c}372' (4..9)
Proj 376 '=IF({c}375="","",{c}375-{c}368)' (4..9); Proj 377 '={c}373/({c}201+{c}200-{c}372)' (4..9); Proj 378 '=IF({c}375="","",{c}373+{c}375-{c}368)' (4..9); Proj 379 '=IF({c}375="","",{c}378/({c}201+{c}200-{c}372-{c}376))' (4..9)
Proj 395 '={c}241' $PRJ; Proj 396 '=+{c}395/{p}395-1' (4..9); Proj 397 ('=$DD${0}*{{c}}395' -f $P.scyre) $PRJ; Proj 398 '={c}397/{c}395' (4..9)
Proj 400 '={c}401+{c}402+{c}403' (4..9); Proj 401 '={c}242' $PRJ; Proj 402 '={c}243' $PRJ; Proj 403 '={c}244' $PRJ
Proj 549 '={c}234' (4..9); Proj 551 '=+{c}550/{c}549' (4..9); Proj 552 '=+({c}550)/{c}669' (4..9); Proj 669 '={c}395' (4..9); Proj 671 '={c}397' (4..9)
# ---------------- valuation
ProjP 'fcfe' ('={{c}}{0}' -f $P.cx) $PRJ $false $NUM
for ($j = 0; $j -lt 5; $j++) { PutP 'ano' (5 + $j) ($j + 1) $false '0' }
ProjP 'fat' ('=1/(1+$DD${0})^{{c}}{1}' -f $P.ke, $P.ano) $PRJ $false '0.000'
ProjP 'vp' ('={{c}}{0}*{{c}}{1}' -f $P.fcfe, $P.fat) $PRJ $false $NUM
PutP 'svp' $BASE ('=SUM(DE{0}:DI{0})' -f $P.vp) $false $NUM
PutP 'tv' $BASE ('=DI{0}*(1+DD{1})/(DD{2}-DD{1})' -f $P.fcfe, $P.gp, $P.ke) $false $NUM
PutP 'pvtv' $BASE ('=DD{0}*DI{1}' -f $P.tv, $P.fat) $false $NUM
PutP 'dl' $BASE '=DA190+DA196-DA174-DA180' $false $NUM
PutP 'eq' $BASE ('=DD{0}+DD{1}-DD{2}' -f $P.svp, $P.pvtv, $P.dl) $false $NUM
PutP 'ps' $BASE ('=DD{0}/DD{1}' -f $P.eq, $P.nsh) $false $R2; $ws.Cells.Item($P.ps, 1).Font.Bold = $true; $ws.Cells.Item($P.ps, 108).Font.Bold = $true
PutP 'vs' $BASE ('=DD{0}/DD{1}-1' -f $P.ps, $P.px) $false $PCT

$xl.Calculate()
# ---------------- âncoras numéricas (aborta sem salvar)
function V($r, $ci) { $x = $ws.Cells.Item($r, $ci).Value2; if ($x -is [double]) { $x } else { [double]::NaN } }
$chk = @(@('receita base', (V 21 108), 9869.52), @('lucro bruto base', ((V 30 108) - (V 29 108)), 3264.6), @('PL base', (V 201 108), 11168.04), @('CR base', (V $P.cr 108), 6524.46), @('estoque obra base', (V $P.est 108), 3961.6), @('lanc base', (V 241 108), 16977.3), @('DL', (V $P.dl 108), 1161.3), @('acoes', (V $P.nsh 108), 435.75))
$bad = @(); foreach ($t in $chk) { if ([double]::IsNaN($t[1]) -or [math]::Abs($t[1] - $t[2]) -gt 0.6) { $bad += ('{0}: {1} (esperado {2})' -f $t[0], $t[1], $t[2]) } }
foreach ($i in 4..9) { $ok = $ws.Cells.Item(204, $ANNI[$i]).Value2; if ($ok -ne $true) { $bad += ('balanco nao fecha em ' + $ANN[$i] + ': ' + ((V 203 $ANNI[$i]) - (V 188 $ANNI[$i]))) } }
if ($bad.Count) { $wb.Close($false); $xl.Quit(); throw ('ancoras fora, nada salvo: ' + ($bad -join '; ')) }
$wb.Save()
# ---------------- leitura
$out = @(); function F($x, $d) { if ($x -is [double]) { if ($d -eq 'p') { '{0:N1}%' -f ($x * 100) } elseif ($d -eq 2) { '{0:N2}' -f $x } else { '{0:N0}' -f $x } } elseif ($null -eq $x) { '' } else { [string]$x } }
function RowOut($r, $d, $from) { $s = ('{0} ' -f $r) + (Lab $r).PadRight(44).Substring(0, 44) + ' |'; foreach ($i in $from..9) { $s += ' ' + (F $ws.Cells.Item($r, $ANNI[$i]).Value2 $d).PadLeft(9) }; $s }
$out += '          2023      2024      2025   2026base    2027      2028      2029      2030      2031'
foreach ($r in 241, 244, 21, 22, 26, 30, 32, 34, 44, 47, 49, 51, 60, 62, 65, 70, 71, 76, 100) { $d = 0; if ($r -in 22, 32, 34, 71, 76) { $d = 'p' }; if ($r -eq 100) { $d = 2 }; $out += (RowOut $r $d 1) }
$out += '--- balanco'; foreach ($r in 174, 175, 181, 176, 182, 185, 188, 192, 197, 200, 201, 203, 204, 207, 208, 211, 345, 349, 355) { $out += (RowOut $r 0 3) }
$out += '--- premissas (coluna base e 2027)'; foreach ($k in 'frec', 'beta', 'sh', 'dias', 'dmap', 'mix', 'jur', 'pfin', 'pfincx', 'pdiv', 'pinv', 'pmin', 'pad', 'scr', 'sest', 'sobra', 'sad', 'salto', 'sout', 'slanc', 'scyre') { $out += ('{0,-8} base={1,10} 2027={2,10}' -f $k, (F $ws.Cells.Item($P[$k], 108).Value2 2), (F $ws.Cells.Item($P[$k], 109).Value2 2)) }
$out += '--- ponte'; foreach ($k in 'lb', 'dcr', 'dest', 'terr', 'dad', 'sga', 'ir', 'fin', 'fincx', 'out', 'div', 'inv', 'min', 'cx', 'rel', 'dist', 'roe') { $d = 0; if ($k -eq 'roe') { $d = 'p' }; $out += (RowOut $P[$k] $d 1) }
$out += '--- valuation'; foreach ($k in 'fcfe', 'fat', 'vp') { $out += (RowOut $P[$k] $(if ($k -eq 'fat') { 2 } else { 0 }) 5) }; foreach ($k in 'svp', 'tv', 'pvtv', 'dl', 'eq', 'ps', 'vs') { $out += ('{0,-6} {1}' -f $k, (F $ws.Cells.Item($P[$k], 108).Value2 $(if ($k -eq 'vs') { 'p' } elseif ($k -eq 'ps') { 2 } else { 0 }))) }
$errs = 0; $vals = $ws.Range($ws.Cells.Item(1, 108), $ws.Cells.Item($r, 113)).Value2; for ($i = 1; $i -le $r; $i++) { for ($j = 1; $j -le 6; $j++) { if ($vals[$i, $j] -is [int] -and $vals[$i, $j] -lt 0) { $errs++; if ($errs -le 10) { $out += ('ERRO linha {0} col {1}: {2}' -f $i, ($j + 107), $vals[$i, $j]) } } } }
$out += ('celulas com erro (cols DD-DI): {0}; abas: {1}' -f $errs, (($wb.Worksheets | ForEach-Object { $_.Name }) -join ' | '))
$wb.Close($true); $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
$out -join "`n"
