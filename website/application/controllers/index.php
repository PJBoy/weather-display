<?php

class Index extends CI_Controller
{
	function __construct()          // Class constructor
	{
		parent::__construct();      // Call parent constructer

		$this->load->database();    // Enable database functions on the default (weather) database
		$this->load->helper(array('cookie', 'url'));    // Enable cookie functions and redirect()
        require 'geoip.inc';            //\
        require 'geoipcity.inc';        //} Enable GeoIP functions
        require 'geoipregionvars.php';  ///
        $this->gi = geoip_open('media/GeoCity.dat', GEOIP_STANDARD);    // Open GeoIP database
	}

    function __destruct()           // Class destructer
    {
        geoip_close($this->gi);     // Close GeoIP database
    }
    
    function __user()   // Private function, returns user if and only if logged in
    {
        $user = get_cookie('user');         // Get the cookie user
		$password = get_cookie('password'); // Get the cookie sha1-encrypted password
        if ($user and $password)            // Presence check
        {
            $this->db->select('password');                                              //\
            $user_data = $this->db->get_where('users', array('user' => $user));         //} Return password data under the user
            if ($user_data->num_rows()>0 && $user_data->row()->password == $password)   //\
                return $user;                                                           //} If user exists and cookie password and database password match, return the user
        }
        return NULL;    // Return NULL if no user found or password mismatch
    }

    function __load_page($short_location)   // This loads all the data that's sent to the webpage
    {
		$data = array();        // Variables to be sent to the view page
		if (!$short_location)   // If URL parameter not given: determine location through IP
		{
            $record = geoip_record_by_addr($this->gi,$_SERVER['REMOTE_ADDR']);  // Get the GeoIP data of the IP
			$this->db->like(array('latitude' => $record['latitude'], 'longitude' => $record['longitude'])); // Find locations with similar coordinates
			$this->db->select('short_location, latitude, longitude');   // Return the short_location, latitude and longitude of the locations
			$query = $this->db->get('Metar', 8);    // Return up to 8 locations from the database
			if (!$query->num_rows()>0)  // If no locations returned:
			{
				$this->load->view('not_found'); // 404 location not found
				return;
			}
            $locations = array();               //\
            foreach($query->result() as $row)   //} Array of short_locations and their coordinates differences from the IP
                $locations["$row->short_location"] = array('latitude' => $row->latitude - $record['latitude'], 'longitude' => $row->longitude - $record['longitude']);
			function square_sort($a, $b)        // Compares the square sum of $a's coordinates with the square sum of $b's coordinates
			{                                   // (a_x²+a_y²)-(b_x²+b_y²) = a_x²-b_x²+a_y²-b_y² = (a_x+b_x)(a_x-b_x)+(a_y+b_y)(a_y-b_y):
                return ($a['latitude'] + $b['latitude']) * ($a['latitude'] - $b['latitude']) + ($a['longitude'] + $b['longitude']) * ($a['longitude'] - $b['longitude']);
			}
            uasort($locations, 'square_sort');  // Sort locations in order of distance from IP
            $short_location = array_slice(array_keys($locations), 0, 1)[0];         // Nearest location
            $data['near_location'] = array_slice(array_keys($locations), 1, 1)[0];  // Second nearest location
            $wind = $this->db->get_where('Metar', array('short_location' => $short_location))->row();	// Get all wind data for the given short_location
		}
        else
        {
            $query = $this->db->get_where('Metar', array('short_location' => $short_location)); // Try to get all wind data for the given short_location
            if (!$query->num_rows()>0)  // If location does not exist:
            {
                redirect('index');     // Determine using IP
                return;
            }
            $wind = $query->row();	    // Get all wind data for the given short_location
            $this->db->select('short_location');                                                    //\
            $next_wind = $this->db->get_where('Metar', array('longitude >' => $wind->longitude));   //} Try to get next row's short_location
            if ($next_wind->num_rows()>0)                                   //\
                $data['near_location'] = $next_wind->row()->short_location; //} If next row exists, use its short_location
            else                                                            // Else use the previous row's short_location
                $data['near_location'] = $this->db->get_where('Metar', array('longitude <' => $wind->longitude))->row()->short_location;
        }
        $data['short_location'] = $short_location;  // Send view page short_location

		// Process simple_wind data
		$data['location'] = "$wind->location ($wind->latitude, $wind->longitude)";  // Send view page location data
        $weather = array(); // Any populated weather and sky data
        if ($wind->weather_intensity)     $weather[] = $wind->weather_intensity;        //\
        if ($wind->weather_descriptor)    $weather[] = $wind->weather_descriptor;       //|
        if ($wind->weather_precipitation) $weather[] = $wind->weather_precipitation;    //|
        if ($wind->weather_obscuration)   $weather[] = $wind->weather_obscuration;      //|
        if ($wind->weather_other)         $weather[] = $wind->weather_other;            //|
        if ($wind->sky_condition_1)       $weather[] = $wind->sky_condition_1;          //} Populate the array with any weather and sky data
        if ($wind->sky_other_1)           $weather[] = $wind->sky_other_1;              //|
        if ($wind->sky_condition_2)       $weather[] = $wind->sky_condition_2;          //|
        if ($wind->sky_other_2)           $weather[] = $wind->sky_other_2;              //|
        if ($wind->sky_condition_3)       $weather[] = $wind->sky_condition_3;          //|
        if ($wind->sky_other_3)           $weather[] = $wind->sky_other_3;              ///
		$data['weather_summary'] = implode(', ', $weather); // Send view page weather and sky data as a comma delimited list
		$directions = array('North', 'North East', 'East', 'South East', 'South', 'South West', 'West', 'North West');  //\
        $data['wind_direction']  = $directions[round(($wind->wind_bearing+$wind->wind_bearing_range/2)/45)%8];          //} Send view page the general direction of the wind
		$data['wind_strength']   = ($wind->wind_knots+$wind->wind_gust_knots)/2;    // Send the view page the average wind strength
		$data['visibility']      = $wind->visibility;   // Send the view page the visibility
		$data['temperature']     = $wind->temperature;  // Send the view page temperature

		// Check to load user data
        $user = $this->__user();    //\
        if ($user)                  //} If logged in user:
        {	// Load user data
            $this->db->select('location');
            $query = $this->db->get_where('favourites', array('user' => $user));
            $data['user']      = TRUE;  // Tell view page to load user content
            $data['locations'] = $query->num_rows()>0 ? $query->result() : NULL;    // Send the view page the user's favourite locations, if any
        }
        else    // User not logged in
            $data['user']      = FALSE; // Tell view page to load non-user content
        
        return $data;
    }

	function index($short_location=NULL)    // Executed on page load
	{
		$data = $this->__load_page($short_location);
		$data['error'] = '';

		$this->load->view('index_view', $data); // Load the view page, with any data
        
        return;
	}

	function favourites_insert($short_location=NULL) // Add URL parameter to user's favourites
	{
        $user = $this->__user();    // Get user
        if ($user)
            $this->db->insert('favourites', array('user'=>$user, 'location'=>$short_location)); // Add to user and short_location to favourites

        redirect("/index/index/$short_location");   // Return to page
	}

	function login($short_location=NULL) // Log user in by setting cookies; parameters are sent through POST
	{
		$data = $this->__load_page($short_location);
        $this->db->select('password');                                                  //\
		$user_data = $this->db->get_where('users', array('user' => $_POST['user']));    //} Load given user's password
		$password = sha1($_POST['password']);   // sha1 encrypt given password
        if (!$user_data->num_rows()>0)          //\
			$data['error'] = 'User not found';  //} User presence check
		else if ($user_data->row()->password != $password)  // If passwords mismatch:
			$data['error'] = 'Incorrect password';
		else    // No errors:
		{
			set_cookie('user', $_POST['user'], '31536000'); //\
			set_cookie('password', $password, '31536000');  //} Set the cookies (arbitrarily for a year)
			$data['error'] = '';
		}

		$this->load->view('index_view', $data);   // Return to page
	}

	function register($short_location=NULL) // (Attempts to) register a user; parameters are sent through POST
	{
		$data = $this->__load_page($short_location);
		if ($this->db->get_where('users', array('user' => $_POST['user']))->num_rows()>0)   //\
			$data['error'] = 'User already exists';                                         //} User overwrite check
		else if (strlen($_POST['user']) < 3)                                //\
			$data['error'] = 'User name must be at least 3 characters';     //} User minimum length check
		else if (strlen($_POST['user']) > 32)                               //\
			$data['error'] = 'User name must be at most 32 characters';     //} User maximum length check
		else if (strlen($_POST['password']) < 6)                            //\
			$data['error'] = 'Password must be at least 6 characters';      //} Password minimum length check
		else if ($_POST['password'] == $_POST['user'])                      //\
			$data['error'] = 'Please choose a more secure password';        //} Password != User check
		else if ($_POST['password'] != $_POST['password2'])                 //\
			$data['error'] = 'Passwords did not match, please try again';   //} Password == Confirm password check
		else    // No errors
		{
			$this->db->insert('users', array('user'=>$_POST['user'], 'password'=>sha1($_POST['password']))); // Add sha1 encrypted password under user
			$data['error'] = '';
		}

		$this->load->view('index_view', $data);   // Return to page
	}

    
    function logout($short_location=NULL)    // Log user out by deleting cookies
    {
        delete_cookie('user');      //\
        delete_cookie('password');  //} Delete cookies
        redirect("/index/index/$short_location");   // Return to page
    }
    
    function help() // Show help webpage
    {
        $this->load->view('help');
    }
}