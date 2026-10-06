# Racional de entregas dentro da CYRE (linhas 176-216, 05/10/2026), na sessão do Excel aberta pelo usuário (GetActiveObject).
# Entregas_t = escala × Σ_i L_i × [F(b_t − i + ½) − F(a_t − 1 − i + ½)], F = normal acumulada do prazo em trimestres (μ, σ por segmento),
# L_i = lançamentos 100% do trimestre i (linhas 325/327/329). Colunas anuais com trimestres na grade são excluídas como origem;
# 2028-31 (só anuais) entram como 4 trimestres virtuais de L/4. Janela [a_t, b_t]: trimestre = ele mesmo; ano = seus 4 trimestres.
# Sazonalidade (média 2018-25) redistribui os trimestres de 2026-27. Linhas 171/172/174 (Entregas VGV 100%) passam a ler o modelo na projeção.
$ErrorActionPreference = 'Stop'
$xl = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application'); $wb = $null; foreach ($w in $xl.Workbooks) { if ($w.Name -match 'CYREMod_2T26') { $wb = $w } }; if (-not $wb) { throw 'CYREMod_2T26 nao esta aberto' }
$ws = $wb.Worksheets.Item('CYRE')
function CL($c) { $c = [int]$c; $s = ''; while ($c -gt 0) { $m = [int](($c - 1) % 26); $s = [string][char](65 + $m) + $s; $c = [int][math]::Floor(($c - 1) / 26) }; $s }
function Chk($row, $pat) { $t = [string]$ws.Cells.Item($row, 1).Value2; if ($t -notmatch $pat) { throw ('linha {0} nao e "{1}": "{2}"' -f $row, $pat, $t) } }
Chk 170 '^Entregas \| VGV 100%'; Chk 171 '^Alto Padrão'; Chk 172 '^Médio'; Chk 173 '^Vivaz Prime'; Chk 174 '^MCMV'; Chk 250 '^Balance Sheet'
Chk 319 '^Lançamentos \| Consolidação'; Chk 320 '^Alto Padrão \| Launches'; Chk 321 '^Médio \| Launches'; Chk 322 '^MCMV 2 e 3 \| Launches'; Chk 324 '^Lançamentos 100% \| com permuta'; Chk 325 '^Alto Padrão'; Chk 327 '^Médio'; Chk 329 '^MCMV'; Chk 338 '^MCMV'
# bloco 176-216 é meu: rótulos da coluna A só podem ser vazios ou meus (auxiliar/premissa/entregas/sazonalidade/prazo/dispersão/escala); então limpa e reescreve
$mine = '^(Entregas · racional|auxiliar:|Premissas da defasagem|prazo médio|dispersão do prazo|escala:|Entregas pelo modelo|entregas modelo|entregas reais|modelo − real|Sazonalidade das entregas|sazonalidade ·|entregas finais)'
for ($r = 176; $r -le 249; $r++) { $t = [string]$ws.Cells.Item($r, 1).Value2; if ($t -and $t -notmatch $mine) { throw "linha $r tem rotulo que nao e meu: $t" } }
$v = $ws.Range($ws.Cells.Item(217, 2), $ws.Cells.Item(249, 125)).Value2; for ($i = 1; $i -le 33; $i++) { for ($j = 1; $j -le 124; $j++) { if ($v[$i, $j] -ne $null) { throw "linha $($i + 216) col $($j + 1) ocupada" } } }
$ws.Range($ws.Cells.Item(176, 1), $ws.Cells.Item(216, 125)).ClearContents() | Out-Null
# ---- colunas: tipo pelo rótulo da linha 2 (xQyy = trimestre; ano = numérico/texto de 4 dígitos)
$C1 = 4; $C2 = 117; $QCOLS = @(); $ACOLS = @{}; $QIDX = @{}; $YEARQ = @{}; $k = 0
for ($c = $C1; $c -le $C2; $c++) { $h = [string]$ws.Cells.Item(2, $c).Value2; $h2 = $h -replace '[^0-9Q]', ''
  if ($h2 -match '^(\d)Q(\d\d)$') { $k++; $QIDX[$c] = $k; $QCOLS += $c; $y = 2000 + [int]$Matches[2]; if (-not $YEARQ.ContainsKey($y)) { $YEARQ[$y] = @() }; $YEARQ[$y] += $k }
  elseif ($h2 -match '^(\d{4})$') { $ACOLS[$c] = [int]$Matches[1] } else { throw "coluna $c sem rotulo de periodo: [$h]" } }
foreach ($c in 109..112) { $ws.Cells.Item(1, $c).Value2 = ('{0}T27' -f ($c - 108)) }   # cabeçalho da linha 1 faltava nos trimestres de 2027
$NEXT = $k + 1   # 1º trimestre virtual de 2028
$BLUE = 16711680; $NUM = $ws.Cells.Item(171, 105).NumberFormat
function Put($r, $c, $f, $blue, $fmt) { $cell = $ws.Cells.Item($r, $c); if ($f -is [double] -or $f -is [int]) { $cell.Formula = ([double]$f).ToString('R', [Globalization.CultureInfo]::InvariantCulture) } else { $cell.Formula = $f }; if ($blue) { $cell.Font.Color = 16711680 } else { $cell.Font.Color = 0 }; if ($fmt) { $cell.NumberFormat = $fmt } }   # literal: variavel na atribuicao COM da "Specified cast is not valid" na instancia ativa
function Lab($r, $t, $bold) { $ws.Cells.Item($r, 1).Value2 = $t; if ($bold) { $ws.Cells.Item($r, 1).Font.Bold = $true } }
# ---- auxiliares (177-183)
Lab 176 'Entregas · racional: lançamentos 100% (linhas 325/327/329) defasados pelo prazo lançamento → entrega (normal em trimestres, por segmento); colunas anuais com trimestres na grade não entram como origem; 2028-31 entram como 4 trimestres virtuais · 05/10/2026' $true
Lab 177 'auxiliar: nº do trimestre (sequencial); anos já cobertos por trimestres = −10000 (excluídos como origem); 2028-31 = 1º trimestre virtual do ano'
Lab 178 'auxiliar: 2º trimestre virtual (só 2028-31)'; Lab 179 'auxiliar: 3º trimestre virtual (só 2028-31)'; Lab 180 'auxiliar: 4º trimestre virtual (só 2028-31)'
Lab 181 'auxiliar: nº de trimestres de origem na coluna (1; 4 nos anos 2028-31)'
Lab 182 'auxiliar: janela de entrega da coluna, 1º trimestre'; Lab 183 'auxiliar: janela de entrega da coluna, último trimestre'
for ($c = $C1; $c -le $C2; $c++) {
  if ($QIDX.ContainsKey($c)) { $i = $QIDX[$c]; Put 177 $c $i $false '0'; Put 178 $c -10000 $false '0'; Put 179 $c -10000 $false '0'; Put 180 $c -10000 $false '0'; Put 181 $c 1 $false '0'; Put 182 $c $i $false '0'; Put 183 $c $i $false '0' }
  else { $y = $ACOLS[$c]
    if ($YEARQ.ContainsKey($y)) { $qs = $YEARQ[$y]; Put 177 $c -10000 $false '0'; Put 178 $c -10000 $false '0'; Put 179 $c -10000 $false '0'; Put 180 $c -10000 $false '0'; Put 181 $c 1 $false '0'; Put 182 $c ($qs | Measure-Object -Minimum).Minimum $false '0'; Put 183 $c ($qs | Measure-Object -Maximum).Maximum $false '0' }
    else { $i0 = $NEXT + 4 * ($y - 2028); Put 177 $c $i0 $false '0'; Put 178 $c ($i0 + 1) $false '0'; Put 179 $c ($i0 + 2) $false '0'; Put 180 $c ($i0 + 3) $false '0'; Put 181 $c 4 $false '0'; Put 182 $c $i0 $false '0'; Put 183 $c ($i0 + 3) $false '0' } } }
# ---- premissas (185-197), valores na coluna DD (108)
Lab 185 'Premissas da defasagem lançamento → entrega (calibradas 2016-25; prazo médio amarrado ao ciclo do modelo de receita: PoC 100% em 42/36/33 meses)' $true
$PRM = @{'Alto Padrão' = @(186, 15.0, 4.0, 0.985, 325); 'Médio' = @(190, 12.5, 1.5, 1.0, 327); 'MCMV 2 e 3 (Vivaz)' = @(194, 13.0, 4.0, 0.756, 329)}
foreach ($s in 'Alto Padrão', 'Médio', 'MCMV 2 e 3 (Vivaz)') { $p = $PRM[$s]; $r = $p[0]
  Lab $r ('prazo médio lançamento → entrega, trimestres · ' + $s); Put $r 108 $p[1] $true '0.0'
  Lab ($r + 1) ('dispersão do prazo (desvio-padrão), trimestres · ' + $s); Put ($r + 1) 108 $p[2] $true '0.0'
  Lab ($r + 2) ('escala: VGV entregue ÷ VGV lançado (preço na entrega, distratos, perímetro) · ' + $s); Put ($r + 2) 108 $p[3] $true '0.000'
  Lab ($r + 3) ('prazo médio em meses · ' + $s); Put ($r + 3) 108 ('=DD{0}*3' -f $r) $false '0' }
# ---- entregas pelo modelo (200-205): alvo = trimestres e anos de 2013 em diante
Lab 199 'Entregas pelo modelo, VGV 100% (R$ mi) · hist. para validação; 3T26 em diante = projeção' $true
$MROW = @{'Alto Padrão' = 200; 'Médio' = 201; 'MCMV 2 e 3 (Vivaz)' = 202}
Lab 200 'entregas modelo · Alto Padrão'; Lab 201 'entregas modelo · Médio (+ Vivaz Prime)'; Lab 202 'entregas modelo · MCMV 2 e 3 (Vivaz)'; Lab 203 'entregas modelo · total'; Lab 204 'entregas reais (linha 170)'; Lab 205 'modelo − real'
$A = (CL $C1); $B = (CL $C2)
function Term($lrow, $idxrow, $X, $mu, $sd) { 'SUMPRODUCT(${0}${1}:${2}${1}/${0}$181:${2}$181,NORM.DIST({3}$183-${0}${4}:${2}${4}+0.5,{5},{6},TRUE)-NORM.DIST({3}$182-1-${0}${4}:${2}${4}+0.5,{5},{6},TRUE))' -f $A, $lrow, $B, $X, $idxrow, $mu, $sd }
$T0 = 4 + 5 * (2013 - 2006)
for ($c = $T0; $c -le $C2; $c++) { $X = CL $c
  foreach ($s in 'Alto Padrão', 'Médio', 'MCMV 2 e 3 (Vivaz)') { $p = $PRM[$s]; $r0 = $p[0]; $mu = ('$DD${0}' -f $r0); $sd = ('$DD${0}' -f ($r0 + 1)); $esc = ('$DD${0}' -f ($r0 + 2)); $lrow = $p[4]
    $f = ('={0}*(' -f $esc) + (Term $lrow 177 $X $mu $sd) + '+' + (Term $lrow 178 $X $mu $sd) + '+' + (Term $lrow 179 $X $mu $sd) + '+' + (Term $lrow 180 $X $mu $sd) + ')'
    Put $MROW[$s] $c $f $false $NUM }
  Put 203 $c ('={0}200+{0}201+{0}202' -f $X) $false $NUM; Put 204 $c ('=IF(COUNT({0}170)=0,"",{0}170)' -f $X) $false $NUM; Put 205 $c ('=IF({0}204="","",{0}203-{0}204)' -f $X) $false $NUM }
# ---- sazonalidade (208-211) e entregas finais (213-216)
Lab 207 'Sazonalidade das entregas dentro do ano (média 2018-25, linha 170) e entregas finais: 3T26-4T27 redistribuídos pela sazonalidade; 2028-31 = modelo' $true
$lab = @('1T', '2T', '3T', '4T')
for ($q = 0; $q -lt 4; $q++) { $terms = @(); foreach ($y in 2018..2025) { $b = 4 + 5 * ($y - 2006); $terms += ('{0}170/{1}170' -f (CL ($b + $q)), (CL ($b + 4))) }; Lab (208 + $q) ('sazonalidade · parcela do ' + $lab[$q] + ' nas entregas do ano'); Put (208 + $q) 108 ('=AVERAGE(' + ($terms -join ',') + ')') $false '0.0%' }
$FROW = @{'Alto Padrão' = 213; 'Médio' = 214; 'MCMV 2 e 3 (Vivaz)' = 215}
Lab 213 'entregas finais · Alto Padrão'; Lab 214 'entregas finais · Médio'; Lab 215 'entregas finais · MCMV 2 e 3 (Vivaz)'; Lab 216 'entregas finais · total'
foreach ($s in 'Alto Padrão', 'Médio', 'MCMV 2 e 3 (Vivaz)') { $m = $MROW[$s]; $fr = $FROW[$s]
  Put $fr 106 ('=(DB{0}+DC{0})*$DD$210/($DD$210+$DD$211)' -f $m) $false $NUM; Put $fr 107 ('=(DB{0}+DC{0})*$DD$211/($DD$210+$DD$211)' -f $m) $false $NUM
  for ($q = 0; $q -lt 4; $q++) { Put $fr (109 + $q) ('=SUM($DE{0}:$DH{0})*$DD${1}' -f $m, (208 + $q)) $false $NUM }
  foreach ($c in 114..117) { Put $fr $c ('={0}{1}' -f (CL $c), $m) $false $NUM } }
foreach ($c in @(106, 107) + (109..112) + (114..117)) { $X = CL $c; Put 216 $c ('={0}213+{0}214+{0}215' -f $X) $false $NUM }
# ---- lançamentos trimestrais de 2027 (1T27-4T27 = ano ÷ 4, sobrescrevível) e cadeia 100% / %CYRE dos trimestres de 2027 copiada do 4T26
foreach ($r in 320, 321, 322) { foreach ($c in 109..112) { Put $r $c ('=$DI{0}/4' -f $r) $false $NUM } }
$ws.Cells.Item(320, 118).Value2 = ([string]$ws.Cells.Item(320, 118).Value2)   # nota do usuário mantida
foreach ($r in 319, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338) { $src = $ws.Cells.Item($r, 107); if ($src.Formula -ne '') { foreach ($c in 109..112) { $ws.Cells.Item($r, $c).FormulaR1C1 = $src.FormulaR1C1; $ws.Cells.Item($r, $c).NumberFormat = $src.NumberFormat } } }
# ---- linhas 170-174 leem o modelo na projeção
foreach ($c in @(106, 107) + (109..112) + (114..117)) { $X = CL $c
  Put 171 $c ('={0}213' -f $X) $false $NUM; Put 172 $c ('={0}214' -f $X) $false $NUM; Put 173 $c 0 $false $NUM; Put 174 $c ('={0}215' -f $X) $false $NUM
  Put 170 $c ('=IF(COUNT({0}171,{0}172,{0}173,{0}174)=0,"",N({0}171)+N({0}172)+N({0}173)+N({0}174))' -f $X) $false $NUM }
foreach ($r in 170..174) { Put $r 108 ('=IF(COUNT(CZ{0}:DC{0})=0,"",SUM(CZ{0}:DC{0}))' -f $r) $false $NUM; Put $r 113 ('=IF(COUNT(DE{0}:DH{0})=0,"",SUM(DE{0}:DH{0}))' -f $r) $false $NUM }
$ws.Range($ws.Cells.Item(176, 1), $ws.Cells.Item(216, 125)).Font.Name = 'Calibri'; $ws.Range($ws.Cells.Item(176, 1), $ws.Cells.Item(216, 125)).Font.Size = 8
$xl.Calculate()
# ---- leitura
$o = @(); $hdr = '    ' + ''.PadRight(34) + ' |'; foreach ($c in 101..117) { $hdr += ' ' + ([string]$ws.Cells.Item(2, $c).Value2).PadLeft(7) }; $o += $hdr
foreach ($r in 320, 322, 324, 325, 177, 181, 182, 183, 200, 201, 202, 203, 204, 213, 214, 215, 216, 170, 171, 172, 174) { $s = ('{0,3} {1}' -f $r, ([string]$ws.Cells.Item($r, 1).Value2).PadRight(34).Substring(0, 34)) + ' |'; foreach ($c in 101..117) { $s += ' ' + $ws.Cells.Item($r, $c).Text.PadLeft(7) }; $o += $s }
$o += '--- validacao anual (modelo x real), colunas anuais 2016-2025:'; foreach ($y in 2016..2025) { $c = 4 + 5 * ($y - 2006); $o += ('{0}: modelo {1} | real {2} | Alto {3}/{4} Medio {5}/{6} MCMV {7}/{8}' -f $y, $ws.Cells.Item(203, $c).Text, $ws.Cells.Item(204, $c).Text, $ws.Cells.Item(200, $c).Text, $ws.Cells.Item(171, $c).Text, $ws.Cells.Item(201, $c).Text, $ws.Cells.Item(172, $c).Text, $ws.Cells.Item(202, $c).Text, $ws.Cells.Item(174, $c).Text) }
$o += ('sazonalidade: ' + (208..211 | ForEach-Object { $ws.Cells.Item($_, 108).Text }) -join ' / ')
$o -join "`n"
