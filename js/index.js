
function getUrlVars() {
	var vars = {};
	var parts = window.location.href.replace(/[?#&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
			vars[key] = value;
	});
	return vars;
}

var id_token = getUrlVars()["id_token"];
console.log('id_token: ' + id_token);

AWS.config.region = 'us-east-1';
AWS.config.credentials = new AWS.CognitoIdentityCredentials({
    IdentityPoolId: 'us-east-1:e7780fbd-3c39-40de-a2fc-8e41d7c3e21f',
    Logins: {
        'cognito-idp.us-east-1.amazonaws.com/us-east-1_KU99vF6aX': id_token
    }
});
var apigClient;
AWS.config.credentials.refresh(function(){
    var accessKeyId = AWS.config.credentials.accessKeyId;
    var secretAccessKey = AWS.config.credentials.secretAccessKey;
    var sessionToken = AWS.config.credentials.sessionToken;
    AWS.config.region = 'us-east-1';
    apigClient = apigClientFactory.newClient({
        accessKey: AWS.config.credentials.accessKeyId,
        secretKey: AWS.config.credentials.secretAccessKey,
        sessionToken: AWS.config.credentials.sessionToken, // this field was missing
        region: 'us-east-1'
    });
});
 

var outputArea = $("#chat-output");


$("#user-input-form").on("submit", function(e) {
  
  e.preventDefault();
  
  var message = $("#user-input").val();
  var body = {
    "message":message
  };
  var params = {
    //This is where any header, path, or querystring request params go. The key is the parameter named as defined in the API

};

var additionalParams = {
  headers: {
    "x-api-key" : 'vBthQe0OmS4fqAPsnoJcL5dWVqCDk00qardGYbl4',
  },
  queryParams: {}
};
  outputArea.append(`
    <div class='bot-message'>
      <div class='message'>
        ${message}
      </div>
    </div>
  `);
  
  
apigClient.chatbotPost(params, body, additionalParams)
    .then(function(result){
        //This is where you would put a success callback
        outputArea.append(`
        <div class='user-message'>
          <div class='message'>
           ${result.data.body}
          </div>
        </div>
      `);
      console.log(result);
    }).catch( function(result){
        //This is where you would put an error callback
        outputArea.append(`
        <div class='user-message'>
          <div class='message'>
           sorry.
          </div>
        </div>
      `);
      console.log(result);
    });
  
  $("#user-input").val("");
  
});



