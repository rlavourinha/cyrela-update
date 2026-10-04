# Leitura (read-only) da aba Projeção do CYREMod_2T26.xlsx: resumo, premissas, motor do cenário 1, valuation, sensibilidade, links na CYRE e contagem de erros.
$ErrorActionPreference = 'Stop'
$path = 'D:\rlavourinha\Pictures\OneDrive\Área de Trabalho\JGP\RLavourinha\2. Homebuilders\1. Modelos\Cyrela\CYREMod_2T26.xlsx'
$xl = New-Object -ComObject Excel.Application; $xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.AskToUpdateLinks = $false
$wb = $xl.Workbooks.Open($path, 0, $true); $ws = $wb.Worksheets.Item('Projeção'); $cy = $wb.Worksheets.Item('CYRE')
$v = $ws.Range($ws.Cells.Item(1, 1), $ws.Cells.Item(260, 22)).Value2
function F($x, $d) { if ($x -is [double]) { if ($d -eq 'p') { ('{0:N1}%' -f ($x * 100)) } elseif ($d -eq 2) { ('{0:N2}' -f $x) } else { ('{0:N0}' -f $x) } } elseif ($x -is [int]) { [string]$x } elseif ($null -eq $x) { '' } else { [string]$x } }
function Row($r, $d, $c1, $c2) { $s = (F $v[$r, 1] 0).PadRight(52).Substring(0, 52) + ' |'; foreach ($c in $c1..$c2) { $s += ' ' + (F $v[$r, $c] $d).PadLeft(9) }; $s }
function RowOf($pattern) { for ($i = 1; $i -le 260; $i++) { $t = $v[$i, 1]; if ($t -and ([string]$t) -match $pattern) { return $i } }; throw ('rotulo nao encontrado: ' + $pattern) }
$R1 = RowOf '^Cenário 1 ·'; $RV = RowOf '^Valuation ·'; $RS = RowOf '^Sensibilidade ·'; $RL = RowOf '^Lançamentos \('
$out = @()
$out += '--- resumo (linhas 8-13)'; foreach ($r in 8..13) { $s = (F $v[$r, 1] 0).PadRight(52).Substring(0, 52) + ' |'; foreach ($c in 4..13) { $x = $v[$r, $c]; $d = 0; if ($c -in 9, 11) { $d = 2 }; if ($c -in 10, 12) { $d = 'p' }; $s += ' ' + (F $x $d).PadLeft(9) }; $out += $s }
$out += '--- premissas (coluna D)'; foreach ($r in 16..56) { $lab = $v[$r, 1]; if (-not $lab) { continue }; $x = $v[$r, 4]; $d = 0; if ($x -is [double] -and [math]::Abs($x) -lt 1.5) { $d = 'p' }; if ($r -in 21, 22, 35) { $d = 2 }; $s = (F $lab 0).PadRight(70).Substring(0, 70) + ' | ' + (F $x $d).PadLeft(10); if ($v[$r, 14] -is [double]) { $s += '   E..H: ' + ((5..8 | ForEach-Object { F $v[$r, $_] 0 }) -join ' ') + '  N: ' + (F $v[$r, 14] 0) }; $out += $s }
$out += '--- lançamentos e mix'; foreach ($r in ($RL + 1)..($R1 - 1)) { if ($v[$r, 1]) { $d = 0; if ($v[$r, 1] -match '^mix') { $d = 'p' }; $out += (Row $r $d 4 13) } }
$out += ('--- cenário 1 (bloco a partir da linha {0}): E..M' -f $R1)
for ($r = $R1 + 1; $r -le $R1 + 37; $r++) { $lab = $v[$r, 1]; if (-not $lab) { continue }; $d = 0; if ($lab -match 'participação|ROE|margem') { $d = 'p' }; if ($lab -match 'por ação|P/L|÷ PL') { $d = 2 }; $out += (Row $r $d 5 13) }
$out += '--- cenários 2-4: receita, caixa, lucro, ROE'
foreach ($k in 2..4) { $R = $R1 + 39 * ($k - 1); $out += ('[' + (F $v[$R, 1] 0) + ']'); foreach ($off in 2, 21, 27, 34) { $d = 0; if ($off -eq 34) { $d = 'p' }; $out += (Row ($R + $off) $d 8 13) } }
$out += '--- valuation'; for ($r = $RV + 2; $r -le $RV + 5; $r++) { if ($v[$r, 1]) { $s = (F $v[$r, 1] 0).PadRight(32) + ' |'; foreach ($c in 9..22) { $x = $v[$r, $c]; $d = 0; if ($c -eq 18) { $d = 2 }; if ($c -in 19, 21) { $d = 'p' }; if ($c -eq 20 -and $x -is [double]) { $x = [math]::Round($x, 1) ; $d = 2 }; $s += ' ' + (F $x $d).PadLeft(8) }; $out += $s } }
$out += '--- sensibilidade (R$/ação, cenário 1)'; for ($r = $RS + 1; $r -le $RS + 8; $r++) { if ($v[$r, 4] -ne $null) { $s = ''; foreach ($c in 4..9) { $x = $v[$r, $c]; $d = 2; if ($c -eq 4 -or $r -eq $RS + 1) { $d = 'p' }; $s += ' ' + (F $x $d).PadLeft(8) }; $out += $s } }
$cv = $cy.Range($cy.Cells.Item(1, 105), $cy.Cells.Item(245, 113)).Value2   # DA..DI
$out += '--- CYRE colunas DA (2T26) e DE..DI (2027E-2031E)'; foreach ($rr in 1, 2, 21, 70, 76, 99, 100, 201, 241) { $s = ('CYRE {0}' -f $rr).PadRight(10) + (F $cy.Cells.Item($rr, 1).Value2 0).PadRight(40).Substring(0, 40) + ' |'; foreach ($c in 1, 5, 6, 7, 8, 9) { $x = $cv[$rr, $c]; $d = 0; if ($rr -eq 76) { $d = 'p' }; if ($rr -eq 100) { $d = 2 }; $s += ' ' + (F $x $d).PadLeft(9) }; $out += $s }
$errs = 0; $ur = $ws.UsedRange.Value2; $rows = $ur.GetLength(0); $cols = $ur.GetLength(1); for ($i = 1; $i -le $rows; $i++) { for ($j = 1; $j -le $cols; $j++) { if ($ur[$i, $j] -is [int] -and $ur[$i, $j] -lt 0) { $errs++; if ($errs -le 10) { $out += ('ERRO em linha {0} coluna {1}: {2}' -f $i, $j, $ur[$i, $j]) } } } }
$out += ('celulas com erro (Int32 negativo = código de erro do Excel): {0}' -f $errs)
$out += ('abas: ' + (($wb.Worksheets | ForEach-Object { $_.Name }) -join ' | '))
$wb.Close($false); $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl)
$out -join "`n"
