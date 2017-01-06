var counter = 1;
var limit = 100;
function addInput(divName){
     if (counter == limit)  {
          alert("You have reached the limit of adding " + counter + " inputs");
     }
     else {
          var newdiv = document.createElement('div');
          newdiv.innerHTML = " <input type='text' name='garage_name[]'>" + " <input type='date' name='from[]'>" + " <input type='date' name='to[]'>" + " <input type='text' name='revenue[]'>" + " <input type='text' name='entries[]'>"+ " <input type='text' name='exits[]'>"+ " <input type='text' name='count[]'>";
          document.getElementById(divName).appendChild(newdiv);
          counter++;
     }
}