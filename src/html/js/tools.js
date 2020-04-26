"use strict";

/**
 * Print timestamped and sourced message to console
 * @param {string} msg Message to print
 * @param {string} src Message source identifier
 */
function print(msg, src=false)
{
    var now = new Date();
    var h = now.getHours().toString().padStart(2, "0");
    var m = now.getMinutes().toString().padStart(2, "0");
    var s = now.getSeconds().toString().padStart(2, "0");
    var ms = now.getMilliseconds().toString().padStart(3, "0");
    var time = `${h}:${m}:${s}.${ms}`;

    var out = `[${time}]`;
    if (src) { out += ` [${src}]`; }
    out += `  ${msg}`;

    console.log(out);
}


/**
 * Send HTTP GET request to specified URL
 * @param {string} url URL to retrieve
 */
function http_get(url)
{
    var xhttp = new XMLHttpRequest();
    xhttp.open("GET", url, false)
    xhttp.send();

    return xhttp.responseText;
}
