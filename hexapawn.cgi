#!/usr/bin/perl
# -*- perl -*-
#
# Play hexapawn
#
# Copyright 1994 M-J. Dominus.
# This is proprietary source code.  However, you are free to copy,
# modify, and distribute this source code, as long as this notice
# remains intact, and as long as your use is non-commercial and
# non-profit.  Commercial and for-profit uses require written permission
# from the author.
#
# M-J. Dominus
# 738C Pine Street 
# Philadelphia, PA 19106-4005
# USA
#
# Fax +1 215 627 5643
#
# mjd@pobox.com
#
# Modifications done by Darren L. VanBuren
# onekopaka+hexapawn@gmail.com
# Modifications include no dependency on ReadParse.pl (it's in the file now)

# Moves in this program are represented this way:
#   0 1 2
#   3 4 5
#   6 7 8
#
# 8-5 white pawn at 8 moves to 5.
# 4x6 black pawn at 4 captures white pawn at 6.
#

use DB_File;
use POSIX qw(/^O_/);
use Carp;

# <META name="description" value="Computer game of `hexapawn' that learns as it goes.">
# <META name="keywords" value="game, toy, strategy, learning, AI">
# <META name="resource-type" value="service">
# <META name="distribution" value="global">

undef %movedb;
$movedbdir = '/srv/web/hexapawnmoves/';

# ReadParse
# Reads in GET or POST data, converts it to unescaped text,
# creates key/value pairs in %in, using '\0' to separate multiple
# selections

# Returns TRUE if there was input, FALSE if there was no input
# UNDEF may be used in the future to indicate some failure.

# Now that cgi scripts can be put in the normal file space, it is useful
# to combine both the form and the script in one place.  If no parameters
# are given (i.e., ReadParse returns FALSE), then a form could be output.

# If a variable-glob parameter (e.g., *cgi_input) is passed to ReadParse,
# information is stored there, rather than in $in, @in, and %in.

sub ReadParse {
  local (*in) = @_ if @_;
  local ($i, $key, $val);

  # Read in text
  if (&MethGet) {
    $in = $ENV{'QUERY_STRING'};
  } elsif (&MethPost) {
    read(STDIN,$in,$ENV{'CONTENT_LENGTH'});
  }

  @in = split(/[&;]/,$in);

  foreach $i (0 .. $#in) {
    # Convert plus's to spaces
    $in[$i] =~ s/\+/ /g;

    # Split into key and value.
    ($key, $val) = split(/=/,$in[$i],2); # splits on the first =.

    # Convert %XX from hex numbers to alphanumeric
    $key =~ s/%(..)/pack("c",hex($1))/ge;
    $val =~ s/%(..)/pack("c",hex($1))/ge;

    # Associate key and value
    $in{$key} .= "\0" if (defined($in{$key})); # \0 is the multiple separator
    $in{$key} .= $val;

  }

  return scalar(@in);
}

# MethGet
# Return true if this cgi call was using the GET request, false otherwise

sub MethGet {
  return ($ENV{'REQUEST_METHOD'} eq "GET");
}


# MethPost
# Return true if this cgi call was using the POST request, false otherwise

sub MethPost {
  return ($ENV{'REQUEST_METHOD'} eq "POST");
}


%textboard = ( 'b', '*', 'w', 'o', 'x', '.');

@whitemoves    = ( '6-3', '7-4', '8-5', '3-0', '4-1', '5-2');
@whitecaptures = ( '6x4', '7x5', '3x1', '4x2', '7x3', '8x4', '4x0', '5x1');
@blackmoves    = ( '3-6', '4-7', '5-8', '0-3', '1-4', '2-5');
@blackcaptures = ( '4x6', '5x7', '1x3', '2x4', '3x7', '4x8', '0x4', '1x5');

srand;

sub print_move {
    local($move) = @_;
    @squarenames = ('a3', 'b3', 'c3', 
		    'a2', 'b2', 'c2', 
		    'a1', 'b1', 'c1');

    local($from, $kind, $to) = ($move =~ /^(.)(.)(.)$/);

    if ($kind eq 'x') {
	return "Pawn at $squarenames[$from] captures pawn at $squarenames[$to].\n";
    } else {
	return "Pawn at $squarenames[$from] moves to $squarenames[$to].\n";
    }
}

sub moves_from {
    local($player, @board) = @_;
    local($otherplayer) = ($player eq 'b') ? 'w' : 'b' ;
    local(@trymoves);
    local ($m);
    local(@legalmoves);

    @trymoves = 
	($player eq 'b') ? 
	    (@blackmoves, @blackcaptures) :
		(@whitemoves, @whitecaptures);
    
    for $m (@trymoves) {
	local($from, $kind, $to) = ($m =~ /^(.)(.)(.)$/);

	@legalmoves = (@legalmoves, $m)
	    if ($kind eq '-' 
		&& $board[$from] eq $player 
		&& $board[$to] eq 'x') ;
	@legalmoves = (@legalmoves, $m)
	    if ($kind eq 'x' 
		&& $board[$from] eq $player 
		&& $board[$to] eq $otherplayer) ;
    }

    return @legalmoves;
}

# Make a given move on a given board and produce the board position
# for the resulting board.
# Assumes move is legal.
sub make_move {
    local($move, @oldboard) = @_;
    local(@board) = @oldboard;

    ($first, $second) = ($move =~ /^(.).(.)$/);

    $board[$second] = $board[$first];
    $board[$first] = 'x';

    return @board;
}

sub hash_board {
    local($oldquote) = $";
    local($hashed);
    $" = '';
    $hashed =  "@_";
    $" = $oldquote;
    return $hashed;
}

# Look one move ahead
# If all moves lose, resign and eliminate this position.
# Otherwise, find a move not known to lose and make it.
sub play {
    local(@board) = @_;
    local(@moves);

    &you_queened(@board) if ($board[0] eq 'w'
			     || $board[1] eq 'w'
			     || $board[2] eq 'w');

    @moves = &moves_from('b', @board);

    # No legal moves
    &i_have_no_moves(@board) unless (@moves);

    @good_moves = ();
    foreach $m (@moves) {
	local(@nextboard) = &make_move($m, @board);
	local($nextboard_hash) = &hash_board(@nextboard);
	unless ($movedb{$nextboard_hash}) {
	    @good_moves = (@good_moves, $m);
	}
    }

    &i_resign(@board) unless (@good_moves);
    
    local($move) = $good_moves[int(rand() * ($#good_moves + 1))];
    
    &move($move, @board);
}

# Really move the piece this time.
# detect wins if necessary
sub move {
    local($my_move, @board) = @_;
    local(@newboard) = &make_move(@_);
    local($newboard_hash) = &hash_board(@newboard);
    local($i, $numwhite);
    local(@yourmoves);

    &i_queen() if ($newboard[6] eq 'b'
		   || $newboard[7] eq 'b'
		   || $newboard[8] eq 'b');

    local($numwhite) = 0;
    for $i (0 .. 8) {
	$numwhite++ if $newboard[$i] eq 'w';
    }

    if ($numwhite == 0) {
	&i_capture_all() ;
    } else {
	@yourmoves = &moves_from('w', @newboard);
	&you_cannot_move() unless(@yourmoves);
    }

    &print_html_header;
    print <<EOM;
<html>
<head>
<title>Hexapawn</title>
</head>

<body bgcolor="#ffffff">
<h1>You Moved To:</h1>
EOM
    &print_board(@board);
    print "<H1>", &print_move($my_move), "</h1>\n";
    &print_board(@newboard);

    if ($i_win) {
	print "<H1>I Win!</h1>\n$success\n";
	print <<EOM;		# 
<a href=\"$0?$tag+start+$$\">Play again</a>? <p>

<hr>

<address>mjd\@plover.com</address>
EOM
    $movedb{'wins'} = $movedb{'wins'} + 1;
    &adjust_streak('W');
    &write_losing_positions; # 
    exit 0;
    }

    print "<h1>Your Legal Moves</H1>\n\n";

    for $i (@yourmoves) {
	local($boardresult) = &hash_board(&make_move($i, @newboard));
	print "<A href=\"$0?$tag+play+$newboard_hash+$boardresult+$$\">";
	print &print_move($i);
	print "</A><p>\n\n";
    }

    print <<EOM;
<hr>
<address>onekopaka+hexapawn\@gmail.com</address>
EOM

    exit 0;
}
    
sub i_have_no_moves {
    $failure = 'I have no legal moves.  I lose.';
    &lose(@_);
}

sub i_resign {
    $failure = 'I don\'t see any good moves.  I resign.';
    &lose(@_);
}

sub you_queened {
    $failure = 'You queened your pawn. You win.';
    &lose(@_);
}

sub adjust_streak {
    local($game) = @_;
    if ($movedb{'streak'} =~ /$game/) {
	$movedb{'streak'} = $movedb{'streak'} . $game;
    } else {
	$movedb{'streak'} = $game;
    }
}

sub lose {
    local(@board) = @_;
    local($losing_board_hash);
    if (@prevboard) {
	$losing_board_hash = &hash_board(@prevboard);
    } else {
	$losing_board_hash = 'bbbxxxwww';
    }
    $movedb{$losing_board_hash} = 1;
    $movedb{'losses'} = $movedb{'losses'} + 1;
    &adjust_streak('L');
    &write_losing_positions;
    
    &print_html_header;
    print <<EOM;
<html>
<head>
<title>Hexapawn: I Lose</title>
</head>
<body bgcolor="#ffffff">
EOM

    &print_board(@board);
    print <<EOM;
<h1>Drat!</h1>

$failure<p>

<a href="$0?$tag+start+$$">Play again</a>? <p>

<hr>
<address>onekopaka+hexapawn\@gmail.com</address>
EOM

    exit 0;
}


sub i_queen {
    $success = "I have queened a pawn.\n";
    $i_win = 1;
    return;
}

sub i_capture_all {
    $success = "I have captured all your pawns.\n";
    $i_win = 1;
    return;
}

sub you_cannot_move {
    $success = "You have no legal moves.\n"; 
    $i_win=1;
    return;
}

sub print_html_header {
    print "content-type: text/html\n\n";
    return;
}

sub read_losing_positions {
    unless ($rc = tie %movedb, DB_File, $movedbfile, O_CREAT|O_RDWR, 0666, $DB_HASH) {
	local($err) = $!;
	&print_html_header;
	print "<title>Error</title>\n";
	print "<h1>Error in <tt>read_losing_positions</h1>\n";
	print "$err ($movedbfile)\n";
	croak;
    }
}

sub write_losing_positions {
    dbmclose(%movedb);
}

sub record {
    local($w, $l) = ($movedb{'wins'} || 0, $movedb{'losses'} || 0);
    local($r);

    if ($w + $l == 0) {
	$r = 0;
    } else {
	$r = $w/($w + $l);
    }
   
    return ($w, $l, sprintf("%.3f", $r));
}
    
sub intro {
    &print_html_header;
    ($wins, $losses, $record) = &record;
    print <<EOM;
<html>
<head>
<title>Hexapawn</title>
</head>

<body bgcolor="#ffffff">
<h1>The Game of Hexapawn</h1>

This is another old traditional computer recreation.
We will play the game of <cite>Hexapawn</cite>.<p>

Initially I am a very bad hexapawn player.  I will choose my move at
random whenever I have a choice.  But I will never make the same mistake
twice.  Whenever I lose, I will get a little better.  So far my record
against the general public is $wins wins and $losses losses, for a
record of $record. <p>

<ul> 
<li> You can <a href="#rules">read the rules</a> of the game, below.
<li> This page
is a searchable index.  If you enter your own name as the search
keywords (Lynx users type `s'), you'll be able to train your own
hexapawn engine from scratch, or pick up where you left off last time.
<li> It typically takes about 50 or 60 games to train a hexapawn engine
to play perfectly. If you're not sure you're interested in playing 50
games of hexapawn this week, you should consider <a
href="$0?General%20Public+start+$$">playing against a public engine</a>
that everyone collaborates on training.
<li> You can <a href="http://github.com/onekopaka/cgi-hexapawn/raw/master/hexapawn.cgi">view the <cite>hexapawn</cite> source code</a>.<p>

</ul>

<isindex>

<a name="rules">
<h2>Rules of Hexapawn</h2>

<cite>Hexapawn</cite></a> is played on a 3x3 board.
Each player has three chess pawns.  
My pawns are black and look like this: <img
src="/~mjd/hexapawn/bw.gif" alt="*" align=middle>.  Your pawns are
white and look like this: <img src="/~mjd/hexapawn/ww.gif" alt="o"
align=middle>. I swiped the pictures of pawns from the program
`gnuchess'.<p>

Initially, the pawns are arranged like this:<p>

EOM
    &print_board('b', 'b', 'b', 'x', 'x', 'x', 'w', 'w', 'w');
    print <<EOM;

When it\'s your turn, you must move one of your pawns.
Pawns move as in chess.
White pawns move up the board and black pawns move down.
Pawns never move backwards.
A pawn may move one square forward if the square ahead of it 
is empty. A pawn may capture an opposing pawn if that pawn is diagonally
ahead of it.    

<p>
EOM
    &print_board('b', 'x', 'x', 'w', 'b', 'x', 'x', 'x', 'w');
    print <<EOM;

<p> For example, suppose it were white\'s turn to move in the position
above.  The white pawn in the lower right corner, at c1, could move a
square forward to c2, or could capture the black pawn in the middle of
the board at b2.  The white pawn at a2 could not move forward, because
the black pawn at a1 is in the way, and it could not capture the black
pawn because the black pawn is directly in front of it; pawns only
capture on the diagonal.  <p> If it were black\'s turn, the black pawn in
the middle of the board could move forward to b1, or could capture the
white pawn at c1.  The black pawn in the corner could not move forward
to a2 because the white pawn is in the way.

<p> A pawn may not move two squares on its first move; pawns never move
more than one square at a time.  Therefore there is no <i>en passant</i>
capture.

<p> When a pawn reaches the other side of the board, it becomes a queen,
as in chess.  When this happens, the player with the queen is deemed to
have won.

<p> If a player has no legal moves on their turn, they lose. 

<p> If this is unclear, please send mail to
<tt>mjd\@plover.com</tt> so he can make it more clear.


<p> Now you are ready to <a href="$0?General%20Public+start+$$">play
hexapawn</a>.<p>

<inc srv "/~mjd/return.html">

<address>mjd\@plover.com</address>
EOM

}

sub start {
    &print_html_header;
    local($wins, $losses, $record) = &record;
    local($streak) = $movedb{'streak'};
    my $WINS = ($wins == 1 ? 'win' : 'wins');
    my $LOSSES = ($losses == 1 ? 'loss' : 'losses');
    print <<EOM;		# 
<html>
<head>
<TITLE>Hexapawn: Start</Title>
</head>

<body bgcolor="#ffffff">
<H1>Game Begins</H1>

I am being trained for \`$movedb{'playername'}\'.
I was created at $movedb{'startdate'}.
So far my record is $wins $WINS and $losses $LOSSES, for a record of
$record.
EOM

    if ($movedb{'forgettings'}) {
	print "My memory has been erased $movedb{'forgettings'} time";
	print (($movedb{'forgettings'} == 1) ? ".\n" : "s.\n");
    }
    print "<p>\n\n";

    if ($streak =~ /WWWWWWWWWW/) {
	print <<EOM;
You have trained me very well, because I have won ten games in a row.
Congratulations.  I can <a href="$0?$tag+forget">forget everything and start over</a> if you want.<p>
EOM
    } elsif ($streak eq '') {

        print "We will discard this engine if you don\'t play
any games for three days.\n<p>";
    } else {

	local($sl) = length($streak);
	local($st) = (($streak =~ /W/) ? 
		      ($sl == 1 ? 'win' : 'wins') : 
		      ($sl == 1 ? 'loss' : 'losses')
		      );

	print "My current winning/losing streak is:  $sl $st.<p>\n\n";

    }

    &print_board('b', 'b', 'b', 'x', 'x', 'x', 'w', 'w', 'w');
    print "You can open with ";
    print "<a href=\"$0?$tag+play+bbbwxxxww\">a1-a2</a>, ";
    print "<a href=\"$0?$tag+play+bbbxwxwxw\">b1-b2</a>, ";
    print "or <a href=\"$0?$tag+play+bbbxxwwwx\">c1-c2</a>";
    if ($movedb{'bbbxxxwww'} == 1) {
	print".  I won\'t go first because I\'ve learned I always lose when I do that.";
    } else {
	print ", or\nyou can <a href=\"$0?$tag+play+bbbxxxwww\">let me have the first move</a>.";
    }
    print "<address>onekopaka+hexapawn\@gmail.com</address>\n";

    exit 0;
}

sub print_board {
    local(@board) = @_;
    local ($i, $j);
    $picpath='/cgi-bin/hexapawn/pix/';
    
    print "<img src=\"${picpath}corner.gif\" alt=\"#\">";
    foreach $i ('a', 'b', 'c') {
	print "<img src=\"${picpath}let$i.gif\" alt=\"$i\">";
    }
    print "<br>\n";

    for $i (0 .. 2) {
	local($ii) = 3 - $i;
	print "<img src=\"${picpath}num$ii.gif\" alt=\"$ii\">";
	for $j (0 .. 2) {
	    local($piece) = $board[$i*3+$j];
	    $picture = $piece . (($j+$i)%2 ? 'b' : 'w') . '.gif';
	    print "<img src=\"$picpath$picture\" alt=\"$textboard{$piece}\">";
	}
	print "<br>\n";
    }
    print "\n<p>\n";
}

############################################################
#
# Main program begins here
#
############################################################

$0 =~ s:.*/::;
#require 'ReadParse.pl';
ReadParse($ENV{QUERY_STRING}, *ARGV);
for ($i=0; $i < @ARGV; $i++) { 
  push @newARGV, split(/ /, $ARGV[$i]);
}
@ARGV = @newARGV;

if ($#ARGV < 0 || $ARGV[0] eq 'intro') {
    $movedbfile = $movedbdir . 'GeneralPublic';
    &read_losing_positions;
    &intro;
    exit 0;
}

while (@ARGV) {
    last if ($ARGV[0] eq 'intro');
    last if ($ARGV[0] eq 'start');
    last if ($ARGV[0] eq 'play');
    last if ($ARGV[0] eq 'forget');
    $movedbfile .= (shift) . ' ';
}

chop $movedbfile;
$playername = $movedbfile;
$movedbfile =~ tr/a-zA-Z0-9//cd;
$tag = $movedbfile;
$movedbfile = $movedbdir . $movedbfile;
&read_losing_positions();
chop($date =`date`);

$movedb{'playername'} = $playername unless ($movedb{'playername'});
$movedb{'startdate'} = $date unless ($movedb{'startdate'});
$movedb{'streak'} = '' unless ($movedb{'streak'});

if ($#ARGV < 0 || $ARGV[0] eq 'start') {	
    &start;
} elsif ($ARGV[0] eq 'dump') {	
    local($board);		
    &print_html_header;
    print "<title>Hexapawn:  Losing positions</title>\n";
    print "<h1>Losing Positions</H1>\n";
    print "There are positions I've learned to avoid: <p>\n";
    while (($board, $junk) = each %movedb) {
	next if ($board eq 'wins' || $board eq 'losses');
	local(@board) = ($board =~ /(.)(.)(.)(.)(.)(.)(.)(.)(.)/);
	&print_board(@board);
    }
    exit 0;
} elsif ($ARGV[0] eq 'forget') {	
    $playername = $movedb{'playername'};
    $date = $movedb{'startdate'};
    $forgettings = $movedb{'forgettings'} || 0;
    open (MAIL, "| /usr/ucb/mail -s \'Hexapawn \"$playername\" forgets\' mjd");
    print MAIL "wins: $movedb{'wins'} losses: $movedb{'losses'}\n";
    print MAIL "streak: $movedb{'streak'} forgettings: $movedb{'forgettings'}\n";
    &write_losing_positions();
    print MAIL "dir: $!\n" unless (open(FOO, "> ${movedbfile}.dir"));
    close FOO;
    print MAIL "pag: $!\n" unless (open(FOO, "> ${movedbfile}.pag"));
    close FOO;
    close MAIL;
    &read_losing_positions();
    chop($date =`date`);
    $movedb{'streak'} = '';
    $movedb{'playername'} = $playername;
    $movedb{'startdate'} = $date;
    $movedb{'forgettings'} = $forgettings + 1;
    &start;
} else {
    shift;
    local($hashed_board, $hashed_prevboard);
    if ($#ARGV < 1) {
	$hashed_board = $ARGV[0];
    } else {		       
	($hashed_board, $hashed_prevboard) = ($ARGV[1], $ARGV[0]);
    }
    local(@board) = ($hashed_board =~ /(.)(.)(.)(.)(.)(.)(.)(.)(.)/);
    @prevboard = ($hashed_prevboard =~ /(.)(.)(.)(.)(.)(.)(.)(.)(.)/);

    &play(@board);
    print "HOW DID I GET HERE?\n\n";
    exit 0;
}

