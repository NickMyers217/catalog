// An IIFE that sets up google sign in and ouath2
(function () {
    // Initialize the auth2 object
    gapi.load('auth2', function () {
	gapi.auth2.init({
	    client_id: '562432597158-ouirs3oa9papg200us2ae0rormi1hkpi.apps.googleusercontent.com'
	}).then(signOut)
    })
})()

// Signs users out of the client side
function signOut () {
    var auth2 = gapi.auth2.getAuthInstance()
    if(auth2.isSignedIn.get()) {
	auth2.signOut()
    }
}

// Callback to sign a user in on the server side
function onSignIn (authResult) {
    if (authResult.code) {
	$('#loginButtons').hide()
	$('#loading').show()
	// Verify the token on the back end via AJAX
	$.ajax({
	    type: 'POST',
	    url: '/googleLogin?state=' + STATE,
	    processData: false,
	    data: authResult.code,
	    contentType: 'application/octet-stream; charset=utf-8',
	    success: function (result) {
		// Handle or verify the server response if necessary.
		if (result) {
		    console.log('Login Successful!<br>'+ result)
		    // Redirect to the home page
		    window.location.replace('/catalog')
		} else if (authResult.error) {
		    console.log('There was an error: ' + authResult.error)
		    flashMessage('There was an error: '+ authResult.error)
		} else {
		    flashMessage('Failed to log in, something is wrong!')
		}
	    },
	    failure: function (result) {
		console.log(result)
		flashMessage(result)
	    }
	})
    }
} 

// Failure callback
function onSignInFailure () {
    console.log('Failed to sign in!');
    flashMessage('Failed to sign in, please try again!')
}
