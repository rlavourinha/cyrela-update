# Custo orçado a incorrer (REF) projetado nas linhas 710 e 716-720 da CYRE (06/10/2026), na sessão aberta do usuário.
# Coortes: lançamentos 100% (325/327/329) × c (custo ÷ VGV, calibrado no 2T26 = 0,44 ≈ 64% de custo × 69% de %CYRE) × fração da obra
# ainda não incorrida [1 − PoC(k)], PoC(k) = p0 + (1−p0) × clip((k − d0)/(μ − d0)), μ = prazo de entrega do bloco de entregas (188/192/196);
# vendidas × estoque pela curva de VSO da coorte s(k) = 1 − (1−s0)(1−q)^k. k = trimestres desde o lançamento (auxiliares 179-185).
$ErrorActionPreference = 'Stop'
$xl = [Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application'); $wb = $null; foreach ($w in $xl.Workbooks) { if ($w.Name -match 'CYREMod_2T26') { $wb = $w } }; if (-not $wb) { throw 'CYREMod_2T26 nao esta aberto' }
$ws = $wb.Worksheets.Item('CYRE')
function CL($c) { $c = [int]$c; $s = ''; while ($c -gt 0) { $m = [int](($c - 1) % 26); $s = [string][char](65 + $m) + $s; $c = [int][math]::Floor(($c - 1) / 26) }; $s }
function Chk($row, $pat) { $t = [string]$ws.Cells.Item($row, 1).Value2; if ($t -notmatch $pat) { throw ('linha {0} nao e "{1}": "{2}"' -f $row, $pat, $t) } }
Chk 710 '^Custo REF a Incorrer'; Chk 716 '^Custos Orçados'; Chk 717 '^vendidas'; Chk 718 '^em estoque$'; Chk 719 '^em estoque - fases lançadas'; Chk 720 '^em estoque - fases não lançadas'
Chk 325 '^Alto Padrão'; Chk 327 '^Médio'; Chk 329 '^MCMV'; Chk 895 '^VPL ÷ preço'; Chk 324 '^Lançamentos 100% \| com permuta'
# linhas do bloco de entregas pelo rótulo (o usuário move linhas)
$labs = $ws.Range($ws.Cells.Item(1, 1), $ws.Cells.Item(1000, 1)).Value2
function RowOf($pat) { for ($i = 1; $i -le 1000; $i++) { $t = [string]$labs[$i, 1]; if ($t -and $t -match $pat) { return $i } }; throw ('rotulo nao encontrado: ' + $pat) }
$IDX0 = RowOf '^auxiliar: nº do trimestre'; $IDX3 = RowOf '^auxiliar: 4º trimestre virtual'; $NQ = RowOf '^auxiliar: nº de trimestres de origem'; $WEND = RowOf '^auxiliar: janela de entrega da coluna, último'
if ($IDX3 -ne $IDX0 + 3) { throw 'auxiliares fora de ordem' }
$MU = @{'Alto Padrão' = (RowOf '^prazo médio lançamento → entrega, trimestres · Alto'); 'Médio' = (RowOf '^prazo médio lançamento → entrega, trimestres · Médio'); 'MCMV 2 e 3 (Vivaz)' = (RowOf '^prazo médio lançamento → entrega, trimestres · MCMV')}
"auxiliares: idx $IDX0-$IDX3, nq $NQ, janela fim $WEND; prazos: $($MU['Alto Padrão']) $($MU['Médio']) $($MU['MCMV 2 e 3 (Vivaz)'])"
$v = $ws.Range($ws.Cells.Item(896, 1), $ws.Cells.Item(915, 125)).Value2; for ($i = 1; $i -le 20; $i++) { for ($j = 1; $j -le 125; $j++) { if ($v[$i, $j] -ne $null) { $t = [string]$v[$i, $j]; if ($t -notmatch '^(Custo orçado a incorrer|custo orçado|PoC inicial|início da obra|vendido no lançamento|venda do saldo)') { throw "linha $($i + 895) col $j ocupada: $t" } } } }
$ws.Range($ws.Cells.Item(897, 1), $ws.Cells.Item(910, 125)).ClearContents() | Out-Null
function Put($r, $c, $f, $blue, $fmt) { $cell = $ws.Cells.Item($r, $c); if ($f -is [double] -or $f -is [int]) { $cell.Formula = ([double]$f).ToString('R', [Globalization.CultureInfo]::InvariantCulture) } else { $cell.Formula = $f }; if ($blue) { $cell.Font.Color = 16711680 } else { $cell.Font.Color = 0 }; if ($fmt) { $cell.NumberFormat = $fmt } }
function Lab($r, $t, $bold) { $ws.Cells.Item($r, 1).Value2 = $t; if ($bold) { $ws.Cells.Item($r, 1).Font.Bold = $true } }
# ---- premissas (897-910), coluna DD
Lab 897 'Custo orçado a incorrer (REF, linhas 710/716-720) · coortes: lançamentos 100% × c × [1 − PoC(k)]; vendidas × estoque pela curva de VSO da coorte; k = trimestres desde o lançamento; prazo de conclusão = prazo de entrega do bloco de entregas' $true
Lab 898 'custo orçado ÷ VGV lançado 100% (c) · calibrado no 2T26 (−11.315): 0,44 ≈ 64% de custo (margem REF 36%) × 69% de %CYRE'; Put 898 108 0.44 $true '0.000'
$SEG = @(@('Alto Padrão', 325, $MU['Alto Padrão'], 0.25, 2, 0.55, 0.08), @('Médio', 327, $MU['Médio'], 0.30, 2, 0.40, 0.15), @('MCMV 2 e 3 (Vivaz)', 329, $MU['MCMV 2 e 3 (Vivaz)'], 0.20, 3, 0.50, 0.18))
$r = 899; $ROWS = @{}
foreach ($s in $SEG) { Lab $r ('PoC inicial no lançamento (terreno, projeto, estande), fração do custo · ' + $s[0]); Put $r 108 $s[3] $true '0.00'; $ROWS[$s[0] + '_p0'] = $r; $r++ }
foreach ($s in $SEG) { Lab $r ('início da obra, trimestres após o lançamento (d0) · ' + $s[0]); Put $r 108 $s[4] $true '0'; $ROWS[$s[0] + '_d0'] = $r; $r++ }
foreach ($s in $SEG) { Lab $r ('vendido no trimestre do lançamento (s0, curva de VSO da coorte) · ' + $s[0]); Put $r 108 $s[5] $true '0.00'; $ROWS[$s[0] + '_s0'] = $r; $r++ }
foreach ($s in $SEG) { Lab $r ('venda do saldo por trimestre (q, curva de VSO da coorte) · ' + $s[0]); Put $r 108 $s[6] $true '0.00'; $ROWS[$s[0] + '_q'] = $r; $r++ }
$ws.Range($ws.Cells.Item(897, 1), $ws.Cells.Item(910, 125)).Font.Name = 'Calibri'; $ws.Range($ws.Cells.Item(897, 1), $ws.Cells.Item(910, 125)).Font.Size = 8
# ---- fórmulas 717 (vendidas) e 718 (em estoque) para DB..DM (106-117)
function Term($X, $L, $idx, $p0, $d0, $mu, $s0, $q, $sold) {
  $K = ('({0}${2}-$D${1}:$DM${1})' -f $X, $idx, $WEND); $KK = ('(({0}>=0)*{0})' -f $K); $XX = ('(({0}-{1})/({2}-{1}))' -f $KK, $d0, $mu)
  $R = ('(1-{0})*(({1}<=0)+({1}>0)*({1}<1)*(1-{1}))' -f $p0, $XX)
  if ($sold) { $S = ('(1-(1-{0})*(1-{1})^{2})' -f $s0, $q, $KK) } else { $S = ('((1-{0})*(1-{1})^{2})' -f $s0, $q, $KK) }
  'SUMPRODUCT($D${0}:$DM${0}/$D${4}:$DM${4},({1}>=0)*{2}*{3})' -f $L, $K, $R, $S, $NQ }
$NUM = $ws.Cells.Item(717, 105).NumberFormat
foreach ($c in 106..117) { $X = CL $c
  foreach ($sold in $true, $false) { $parts = @()
    foreach ($s in $SEG) { $nm = $s[0]; $p0 = ('$DD${0}' -f $ROWS[$nm + '_p0']); $d0 = ('$DD${0}' -f $ROWS[$nm + '_d0']); $mu = ('$DD${0}' -f $s[2]); $s0 = ('$DD${0}' -f $ROWS[$nm + '_s0']); $q = ('$DD${0}' -f $ROWS[$nm + '_q'])
      foreach ($idx in $IDX0..$IDX3) { $parts += (Term $X $s[1] $idx $p0 $d0 $mu $s0 $q $sold) } }
    $row = 718; if ($sold) { $row = 717 }
    Put $row $c ('=-$DD$898*(' + ($parts -join '+') + ')') $false $NUM }
  Put 716 $c ('={0}717+{0}718' -f $X) $false $NUM; Put 719 $c ('={0}718' -f $X) $false $NUM; Put 720 $c 0 $false $NUM; Put 710 $c ('={0}716' -f $X) $false $NUM }
$ws.Cells.Item(716, 1).Value2 = 'Custos Orçados (proj.: = vendidas + em estoque, coortes; linhas 897-910)'
$ws.Cells.Item(719, 1).Value2 = 'em estoque - fases lançadas (proj.: = em estoque; o modelo só tem fases lançadas)'
$ws.Cells.Item(720, 1).Value2 = 'em estoque - fases não lançadas (proj.: 0)'
$xl.Calculate()
$o = @(); $hdr = '    ' + ''.PadRight(40) + ' |'; foreach ($c in 101..117) { $hdr += ' ' + ([string]$ws.Cells.Item(2, $c).Value2).PadLeft(7) }; $o += $hdr
foreach ($rr in 710, 716, 717, 718, 719, 720) { $s = ('{0,3} {1}' -f $rr, ([string]$ws.Cells.Item($rr, 1).Value2).PadRight(40).Substring(0, 40)) + ' |'; foreach ($c in 101..117) { $s += ' ' + $ws.Cells.Item($rr, $c).Text.PadLeft(7) }; $o += $s }
$o += ('tamanho da formula DB717: ' + ([string]$ws.Cells.Item(717, 106).Formula).Length + ' caracteres')
$o -join "`n"
