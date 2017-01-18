#!/usr/bin/env python
import cgi
form = cgi.FieldStorage()

# getlist() returns a list containing the
# values of the fields with the given name
colors = form.getlist('color')

print """Content-Type: text/html\n
<html>

<head><meta charset="UTF-8"><title>Smarking checking</title> <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/meyer-reset/2.0/reset.min.css"><link rel='stylesheet prefetch' href='http://fonts.googleapis.com/css?family=Roboto:400,100,300,500,700,900|RobotoDraft:400,100,300,500,700,900'><link rel='stylesheet prefetch' href='http://maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css'><link rel="stylesheet" href="/css/style.css">
<style>
input[type=checkbox]:checked + label.strikethrough{
  text-decoration: line-through;
}
.form-module submit {
  cursor: pointer;
  background: #33b5e5;
  width: 100%;
  border: 0;
  padding: 10px 15px;
  color: #ffffff;
  -webkit-transition: 0.3s ease;
  transition: 0.3s ease;
}
.form-module submit:hover {
  background: #178ab4;
}
</style>
</head>


<body>"""

print """<div class="pen-title">
    <p><img src="/logo-s.png"><h2 style="color:darkcyan;font-size: 20px;">Your choices have been saved.  Thank you. </h2></p></div>
"""

f=open("false_positives", "a+")

for color in colors:
    f.write(cgi.escape(color)+"\n")

print '<p><a href = "../index.html">Go back to home page</a></p>'
print '</form></body></html>'
