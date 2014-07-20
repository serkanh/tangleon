/*
* JQuery util functions
*
* Author: Faraz Masood Khan
*/

String.prototype.trim = String.prototype.trim || function () {
    return this.replace(/^\s+|\s+$/g, "");
};

String.prototype.ltrim = String.prototype.ltrim || function () {
    return this.replace(/^\s+/, "");
};

String.prototype.rtrim = String.prototype.rtrim || function () {
    return this.replace(/\s+$/, "");
};

String.prototype.fulltrim = String.prototype.fulltrim || function () {
    return this.replace(/^[\n\s]+|[\s\n]+$/g, "").replace(/\s+/g, " ");
};

function stringToColor(str) {

    // str to hash
    str = "   " + str;
    for (var i = 0, hash = 0; i < str.length; hash = str.charCodeAt(i++) + ((hash << 5) - hash));

    // int/hash to hex
    for (var i = 0, color = "#"; i < 3; color += ("00" + ((hash >> i++ * 8) & 0xFF).toString(16)).slice(-2));

    return color;
}

// Update post vote for user action
function update_vote(data) {
    if (data.status == 200) {
        response = JSON.parse(data.responseText);
        votes = parseInt($('#post-id-' + response.post_id + ' .votes').html()) + response.net_effect;        
        $('#post-id-' + response.post_id + ' .votes').html(votes);
        
        if (response.vote_index == 1)	{
				if (!$('#post-id-' + response.post_id + ' .up-vote').hasClass('up-vote-on'))        		
        			$('#post-id-' + response.post_id + ' .up-vote').addClass('up-vote-on');
        		
        		$('#post-id-' + response.post_id + ' .down-vote').removeClass('down-vote-on');
        } else if (response.vote_index == -1) {
        		$('#post-id-' + response.post_id + ' .up-vote').removeClass('up-vote-on');
        		
        		if (!$('#post-id-' + response.post_id + ' .down-vote').hasClass('down-vote-on'))
        			$('#post-id-' + response.post_id + ' .down-vote').addClass('down-vote-on');
        } else {
        		$('#post-id-' + response.post_id + ' .up-vote').removeClass('up-vote-on');
        		$('#post-id-' + response.post_id + ' .down-vote').removeClass('down-vote-on');
        }
        
    } else if (data.status == 403) {
           window.location = data.responseText;                    
    } else {
           window.location = '/';
    }
}

// Update comment vote for user action
function update_comment_vote(data) {
    if (data.status == 200) {
        response = JSON.parse(data.responseText);
        votes = parseInt($('#comment-id-' + response.comment_id + ' .votes').first().html()) + response.net_effect;        
        $('#comment-id-' + response.comment_id + ' .votes').first().html(votes);
        
        if (response.vote_index == 1)	{
				if (!$('#comment-id-' + response.comment_id + ' .up-vote').first().hasClass('up-vote-on'))        		
        			$('#comment-id-' + response.comment_id + ' .up-vote').first().addClass('up-vote-on');
        		
        		$('#comment-id-' + response.comment_id + ' .down-vote').first().removeClass('down-vote-on');
        } else if (response.vote_index == -1) {
        		$('#comment-id-' + response.comment_id + ' .up-vote').first().removeClass('up-vote-on');
        		
        		if (!$('#comment-id-' + response.comment_id + ' .down-vote').first().hasClass('down-vote-on'))
        			$('#comment-id-' + response.comment_id + ' .down-vote').first().addClass('down-vote-on');
        } else {
        		$('#comment-id-' + response.comment_id + ' .up-vote').first().removeClass('up-vote-on');
        		$('#comment-id-' + response.comment_id + ' .down-vote').first().removeClass('down-vote-on');
        }
        
    } else if (data.status == 403) {
           window.location = data.responseText;                    
    } else {
           window.location = '/';
    }
}