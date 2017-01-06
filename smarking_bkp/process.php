<!DOCTYPE html>
<html>
<body>

<?php
$garagenames = $_POST["garage_name"];
$from = $_POST["from"];
$to = $_POST["to"];
$revenue = $_POST["revenue"];
$entries = $_POST["entries"];
$exits = $_POST["exits"];
$count = $_POST["count"];



$num_elements = count($garagenames);

//create a string to put into the file
$file_data="";
for ($i = 0; $i < $num_elements; $i++) {
    $file_data.= $garagenames[$i];
    $file_data.= ",";
    $file_data.= $from[$i];
    $file_data.= ",";
    $file_data.= $to[$i];
    $file_data.= ",";
    $file_data.= $revenue[$i];
    $file_data.= ",";
    $file_data.= $entries[$i];
    $file_data.= ",";
    $file_data.= $exits[$i];
    $file_data.= ",";
    $file_data.= $count[$i];
    $file_data.= "\n";
}

#write the output to a file
file_put_contents("AM_request", $file_data);

$python = `python process.py`;
echo $python;

?>
    

</body>
</html>