## Takes two input files, one with F5 virtual server info on one line (command to gather info below)
## and the other with F5 pool data (command to gather info below). Munges the config info to see
## vs-name, destination, pool-name, and pool members
# tmsh list ltm virtual destination | grep -E "ltm virtual|destination" | tr '\n' ' ' | sed 's/ltm virtual/\nltm virtual/g;s/\s\+/ /g' | grep -v "pool none" > vs.out
# tmsh list ltm pool | grep -E "ltm pool|address" | tr '\n' ' ' | sed 's/ltm pool/\nltm pool/g;s/ \+/ /g;s/ address / /g'
open VIPS, '<vs.out';

while (<VIPS>) {
  chomp;
  my($vs_name, $vs_dest, $pool_name) = /ltm virtual (.*?) \{ destination (.*?):.+? pool (.*)(\s|$)/;
  if ($pool_name == " ") {
	  print $pool_name;
  }
  open POOLS, '<pools.out';
  foreach $line (<POOLS>) {
    chomp $line;
    # surround pool_name with spaces for search
    if (index($line, ' ' . $pool_name . ' ') >= 0) {
      @pool_line = split /{ /, $line;
      @members = split / /, @pool_line[1];
    }
  }
  close POOLS;
  foreach $member (@members) {
    print "$vs_name $vs_dest $pool_name $member\n";
  }
  #print "VS:\t\t$vs_name\n";
  #print "Dest:\t\t$vs_dest\n";
  #print "Pool:\t\t$pool_name\n";
  #print "Members:\n";
  #print "$members\n";

  #print "\n";
}

close VIPS;
