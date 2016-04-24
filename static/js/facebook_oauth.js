// Facebook sign in callback
function sendTokenToServer() {
    var accessToken = FB.getAuthResponse().accessToken
    $('#loginButtons').hide()
    $('#loading').show()
    FB.api('/me', function (response) {
	$.ajax({
	    type: 'POST',
	    url: '/fbLogin?state=' + STATE,
	    processData: false,
	    data: accessToken,
	    contentType: 'application/octet-stream; charset=utf-8',
	    success: function (result) {
		// Handle or verify the server response if necessary.
		if (result) {
		    console.log('Login Successful!<br>'+ result)
		    // Redirect to the home page
		    window.location.replace('/catalog')
		} else {
		    flashMessage('Failed to log in, something is wrong!')
		}
	    }
	})
    })
}

// Initialize the Facebook SDK
window.fbAsyncInit = function() {
    FB.init({
      appId      : '230958487259678',
      xfbml      : true,
      version    : 'v2.5'
    });
};
(function(d, s, id){
   var js, fjs = d.getElementsByTagName(s)[0];
   if (d.getElementById(id)) {return;}
   js = d.createElement(s); js.id = id;
   js.src = "//connect.facebook.net/en_US/sdk.js";
   fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));
