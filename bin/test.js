var loggly = require('loggly');

var config = {
    subdomain: this.config[i].subdomain,
    auth: {
      username: this.config[i].username,
      password: this.config[i].password
    },
    json: true
};
var logger = loggly.createClient(config);

