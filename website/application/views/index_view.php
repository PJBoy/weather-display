<html>
<script>
function ShowLogin(short_location)
{
	var Login = document.getElementById("Login");
	var LoginForm = document.createElement("span");
	LoginForm.innerHTML = "" +
		"<form action=/index/login/"+short_location+" method=post style=display:inline>" +
        "Username: <input type=text name=user> Password: <input type=password name=password>" +
		"<input type=submit value=Login>" +
		"</form>";
	Login.parentNode.insertBefore(LoginForm, Login);
	Login.parentNode.removeChild(Login);
	
	return;
}
function ShowRegister(short_location)
{
	var Register = document.getElementById("Register");
	var RegisterForm = document.createElement("span");
	RegisterForm.innerHTML = "" +
		"<form action=/index/register/"+short_location+" method=post style=display:inline>" +
        "Username: <input type=text name=user> Password: <input type=password name=password> Confirm password: <input type=password name=password2>" +
		"<input type=submit value=Register>" +
		"</form>";
	Register.parentNode.insertBefore(RegisterForm, Register);
	Register.parentNode.removeChild(Register);
	
	return;
}
</script>
<title>Index</title>
<style>table{border-spacing:0;} td{padding-left:4px;padding-right:4px;border-width:1px;}</style>


<table align=center>
    <tr><td colspan=2 align=center style="border-bottom-style:solid; border-width:2px;">
        <img style=display:block src=/media/welcome.png></img>
        <?php
        if ($error)
            echo "<p>Error: $error</p>";
        ?>
        <a href=/index>Home</a> 
        <a href=/index/help>Help</a> 
        <?php echo ($user ?
        "<a href=/uac>User account control</a> <a href=/index/logout/$short_location>Logout</a>" :
        "<a href=# id=Login onclick=ShowLogin('$short_location')>Login</a> <a href=# id=Register onclick=ShowRegister('$short_location')>Register</a>");?> 
        <a href=# onclick=ShowSearch>Search</a> 
        <a href=# onclick=ShowCSS>CSS</a>
    </td></tr>
    <tr><?php
        if ($user)
        {
            echo '<td valign=top style=border-right-style:solid;>';
            echo '<p>Favourite locations:<br>';
            echo '<ul>';
            if ($locations)
                foreach($locations as $fav)
                    echo "<li><a href=/index/index/$fav->location>$fav->location</a></li>";
            echo '</ul>';
            echo "<a href=/index/favourites_insert/$short_location>Add $short_location to favourites</a>";
        }
        else
            echo '<td>';
		?>
    </td><td>
    	<p><?=$location?> - See also: <a href=/index/index/<?=$near_location?>><?=$near_location?></a></p>
		<table><?php
			if ($wind_direction)  echo "<tr><td style=border-right-style:solid;>Wind direction</td><td>$wind_direction</tr>";
			if ($wind_strength)   echo "<tr><td style=border-right-style:solid;>Wind strength</td> <td>$wind_strength knot</tr>";
			if ($visibility)      echo "<tr><td style=border-right-style:solid;>Visibility</td>    <td>$visibility miles</tr>";
			if ($weather_summary) echo "<tr><td style=border-right-style:solid;>Weather</td>       <td>$weather_summary</tr>";
			if ($temperature)     echo "<tr><td style=border-right-style:solid;>Temperature</td>   <td>{$temperature}°C</tr>";
		?></table>
        <a href=# onclick=ShowWind>See more</a>
        
    </td></tr>


</html>