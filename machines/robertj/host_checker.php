<html>
<head>

<style>
.down {
background: #ff0000;
width: 15px;
height: 15px;
border-radius: 50%;
}​
</style>

<style>
.up {
background: #00ff00;
width: 15px;
height: 15px;
border-radius: 50%;
}​

</style>

</head>

<body>
<?php
#exec('python snapshot.py',$output);
exec('python2 host_status.py',$output);
#passthru('python host_status.py');

echo("<table border=1 padding=5>");
echo("<tr><th>&nbsp;</th><th>Hostname</th><th>Uptime</th><th>Description</th><th>OS</th></tr>");
for ($i=0;$i<sizeof($output)-1;$i++){
  $row = explode(';',$output[$i]);
  echo("<tr>");
  $color = ($row[1] == 0) ? "\"down\"" : "\"up\"";
  echo("<td class=" . $color . ">&nbsp;</td>");
  echo("<td>" . $row[0] . "</td>");
  $uptime = ($row[1] == 0) ? "<b>Host is down</b>" : $row[2];
  echo("<td>" . $uptime . "</td>");
  echo("<td>" . $row[3] . "</td>");
  echo("<td>" . $row[4] . "</td>");
  echo("</tr>\n");
}
echo("</table>");
?>
</body>
</html>
