/*
 * jQuery Plugin: Image viewer plugin
 * Version 1.0
 *
 * Copyright (c) 2013 Faraz Masood Khan (http://www.tangleon.com),
 * All rights reserved.
 */

$.fn.imageViewer = function() {
	// Setting max height and width with respect to screen size
	$('#iv_image').css('max-width', (screen.width * 0.80) + 'px');
	$('#iv_image').css('max-height', (screen.height* 0.80) + 'px');
	$(this).click(function(e) {
		e.preventDefault();
		var src = $(this).attr('iv_src');
		if (src == '')
			src = $(this).attr('src');

		var visit_link = $(this).attr('iv_visit_link');
		if (visit_link == '')
			visit_link = src;

		var comment_link = $(this).attr('iv_comment_link');
		if (comment_link == '')
			comment_link = '#';

		$('#iv_image').attr('src', src);
		$('#iv_visit_link').attr('href', visit_link);
		$('#iv_comment_link').attr('href', comment_link);
		$('#iv_container').fadeIn('fast');
	});
};

$('#iv_container').click(function(e) {
	if (!$(e.target).parents().andSelf().is('#iv_content'))
		$(this).fadeOut('fast');
});

