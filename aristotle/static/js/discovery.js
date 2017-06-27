function AddCartItem(anchor_tag,record_id) {
  var data = 'record_id=' + record_id;
  $.ajax({
      type: 'get',
       url: '/catalog/cart/add',
      data: data,
   success: function(responseText) {
       // Should change icon and text to Drop
       var anchor_html = "DropCartItem(this,'" + record_id + "'," + true + ')';
       $(anchor_tag).removeClass('label-success').addClass('label-important');
       $(anchor_tag).attr('onclick',anchor_html);
       $(anchor_tag).attr('title','Remove Record from cart');
       $(anchor_tag).html('<i class="icon-minus-sign icon-white"></i>');
    }
   });
}


function CartToRefworks(session_id) {
  var refworks_url = 'http://www.refworks.com/express/expressimport.asp?vendor=iii&filter=RefWorks%20Tagged%20Format&url=http%3A//' + window.location.host + '/catalog/cart/refworks?session=' + session_id;
  window.open(refworks_url);
}


function ChangeSearchBookText(btn_text) {
 $("#searchby").html(btn_text);
 $("#searchby").val(btn_text);
 var search_char = btn_text.charAt(0);
 switch(search_char) {
  case 'A':
   $('#search-type').val("author_search");
   break;
  case 'J':
   $('#search-type').val("title_search");
   break;
  case 'K':
   $('#search-type').val("search");
   break;
  case 'S':
   $('#search-type').val("subject_search");
   break;
  case 'T':
   $('#search-type').val("title_search");
 }
}

function DropCartItem(anchor_tag,record_id,keep) {
  var data = 'record_id=' + record_id;
  $.ajax({
      type: 'get',
       url: '/catalog/cart/drop',
      data: data,
   success: function(responseText) {
       // Should change icon and text to Drop
       if(keep) {
         var anchor_html = "AddCartItem(this,'" + record_id + "'" + ')';
         $(anchor_tag).removeClass('label-important').addClass('label-success');
         $(anchor_tag).attr('onclick',anchor_html);
         $(anchor_tag).attr('title','Remove Record from cart');
         $(anchor_tag).html('<i class="icon-plus-sign icon-white"></i>');
       } else {
         $(anchor_tag).parent().remove();
       }
    }
   });
}

function DisplayAdvSearch(search_a) {
  $('#adv-searchbox').attr('style','display:inline');
  $('#basic-searchbox').attr('style','display:none');
  $(search_a).text('Basic Search');
  
}


function DisplayBasicSearch(search_a) {
  $('#adv-searchbox').attr('style','display:none');
  $('#basic-searchbox').attr('style','display:inline');
  $(search_a).text('Advanced Search');
}

function DisplayFacet(facet_a) {
 // Cycle through and close other facets

 var h5 = $(facet_a).children()[0];
 var ul = $(facet_a).next();
 if($(h5).attr('class') == 'closed') {
   $(h5).attr('class','');
   $(ul).attr('class','open');
 } else {
   $(h5).attr('class','closed');
   $(ul).attr('class','closed');
 }
 return false;
}

function DisplayItems(more_dd) {
  $("dd").attr('style','');
  $(more_dd).remove();
}

function DisplayAllItems(record_id) {
  var data = "record_id=" + record_id;
  $("#all-items-dlg").modal('show');

  $.ajax({
     type: 'get',
      url: '/catalog/ajax/items',
     data: data,
    success: function(responseText) {
      $("#all-items-dlg").html(responseText);
     }
    });

}

function DisplayRows(row_count_select) {
 var new_row_count = $(row_count_select).attr('value');
 $('#solr_rows').attr('value',new_row_count);
 document.forms['catalog_search'].submit();

}

function DisplaySearch(search_a) {
   var label = $(search_a).text();
   if(label == 'Basic Search') {
      DisplayBasicSearch(search_a);
   }
   if(label == 'Advanced Search') {
      DisplayAdvSearch(search_a);
   }

}

function EmailCart() {
  var email_addr = prompt('Please enter your email');
  var data = 'email=' + email_addr;
  $.ajax({
     type: 'get',
      url: '/catalog/cart/email',
     data: data,
    success: function(responseText) {
          alert(responseText);
     }
    });
}

function FilterByFacet(facet,value) {
 $('#catalog_search').append('<input type="hidden" name="fq" value="' + facet + ':' + value + '">');
 document.forms['catalog_search'].submit();

}

function handleResultPaginateClick(new_page_index,pagination_container) {
  var data = 'func=search&search-type=' + $("input[name~='search-type']").val();
  data += '&page_index=' + new_page_index;
  data += '&rows=' + $("#solr_rows").val();
  $("input[name~='q']").each(
    function(i,v) {
     data += '&q=' + $(v).val();
  });
  $("input[name~='fq']").each(
    function(i,v) {
      data += '&fq=' + $(v).val();
  });
  $.ajax({
      type: 'get',
       url: '/catalog/rpc',
      data: data,
   success: function(responseText) {
      $('.results-list').remove();
      $('#main-content').attr('innerHTML',responseText);
    }
   });

  return false;
}


function ProcessSearchQuery() {
  var new_q = $('#book-search').value();
  new_q += set_fieldname("field1");
  new_q += set_fieldname("field2");
  new_q += set_fieldname("field3");
  $('#book-search').attr('value',new_q);
  //document.forms['catalog_search'].submit();
}

function set_fieldname(field_stem) {
  var search_type = "input[name~='" + field_stem + "_type']";
  var search_phrase = "input[name~='" + field_stem + "_phrase']";
  var search_operator = "input[name~='" + field_stem + "_operator']";

  var output = ' ';
  if ($(search_type).value()) {
    output += $(search_type).value() + ':' + $(search_phrase).value();
  } else {
    output += $(search_phrase).value();
  }
  if (output.length > 2) {
    output += ' ' + $(search_operator).value();
  }
 return output;
}


function PrintCart() {
  var print_window = window.open('/catalog/cart/print','_blank','fullscreen=yes');
  print_window.print();
}

function ShowCart(session_id) {
   var data = '';
   $.ajax({
      type: 'get',
       url: '/catalog/cart',
      data: data,
   success: function(responseText) {
        var output = '<button class="btn" onclick="PrintCart()"><i class="icon-print"></i> Print</button>';
        output += '<button class="btn" onclick="EmailCart()"><i class="icon-envelope"></i> Email</button>';
        output += '<button class="btn" onclick=';
        output += "'CartToRefworks(";
        output += '"' + session_id + '"';
        output += ")'><i class='icon-share'></i> Export to RefWorks</button><ol>";
        var results = eval(responseText);
        for(row in results) {
           var record = results[row];
           if(record.id) {
             output += '<li><a href="/catalog/record/' + record.id + '"><em>';
             output += record.full_title + '</em></a>.';
             if(record.format) {
                output += record.format + ' ';
             }
             if(record.callnum) {
               output += record.callnum + ' at ';
             }

             if(record.location) {
                output +=  record.location;
             }
             output += '. <a class="btn btn-mini btn-danger" onclick="DropCartItem(this,' + "'" + record.id + "'," + false + ')">';
             output += 'Remove</a>';
           }
           
        }
        output += '</ol>';
        $('#cart-dlg-contents').html(output);
    }
   });

}

function toggle_num_search() {
  window.location = "/catalog/search?search_type=" + $("#search_type").val();
}

var simpleViewModel = function() {
  var self = this;
  self.searchingOptions =  [
      { name: "Keyword", search_type: "search" },
      { name: "Author", search_type: "author_search" },
      { name: "Title", search_type: "title_search" },
      { name: "Subject", search_type: "subject_search" },
      { name: "Number", search_type: "number_search" }
   ];
  self.numberOptions = [
      { name: "pid", number_type: "PID" },
      { name: "doi", number_type: "DOI" }
   ];

  self.booleanConnectors = [
    { name: "and", bool_type: "and"},
    { name: "or", bool_type: "or"},
    { name: "not", bool_type: "not"},
  ];

  self.activeFacet = ko.observable();
  self.activeFacetValue = ko.observable();
  self.chosenNumberOption = ko.observable();
  self.chosenSearch = ko.observable();
  self.chosenNumberOption = ko.observable();
  self.exactSearch = ko.observable();
  self.facets = ko.observableArray();
  self.searchQuery = ko.observable();
  self.shouldShowNumber = ko.observable(false);
  self.displayResults = ko.observable();
  self.searchResults = ko.observableArray();
  self.searchMessage = ko.observable();
  self.isDetailed = ko.observable();
  self.source = ko.observable();
  self.totalHits = ko.observable();
  self.fromOffset = ko.observable(0);
  self.shardSize = ko.observable(15);
  self.searchMode = ko.observable("search"); // Should be either search, facet, or browse
  self.searchPlaceholder = ko.observable("Search DigitalCC");

  self.creatorSearch = function() {


  }

  self.addSearchRow = function() {
    var lastDiv = $("#add-row").prev('div');
    var new_row = document.createElement("div");
    $(new_row).addClass("row");
    var new_bool_div = document.createElement("div");
    new_bool_div.class = "col-xs-3";
    var select_bool = document.createElement("select");
    select_bool.class = "form-control";
    new_row.appendChild(select_bool);
    console.log("Before lastDiv appendChild " + new_row.length());
    lastDiv.appendChild(new_row);
}


  self.showAbstract = function(abstract_) {
     console.log(abstract_);
     //$(this.parent).html(abstract_);
  }

  self.processAggregation = function(name, agg) {
    var facetSlug = name.toLowerCase()
                         .replace(/[^a-zA-Z0-9]+/g, "-");
    var buckets = ko.observableArray();
   for(j in agg["buckets"]) {
     var bucket = agg["buckets"][j];
     buckets.push({"bucketName": bucket["key"],
                   "bucketCount": bucket["doc_count"]});
   }
   return {"facetSlug": facetSlug,
           "facetName": name,
           "buckets": buckets}
  }



  self.processResult = function(source) {
      var summary_limit = 400;
      var child_pid = source["pid"];
      var abstract_display = "";
      if (source["abstract"]) {
        var abstract_display = String(source["abstract"]);
	  }
      if (abstract_display.length >= summary_limit) {
          var firstChars = abstract_display.substring(0, summary_limit);
		  abstract_display = firstChars + "<a href='#' data-bind='click: showAbstract.bind($data, '" + abstract_display + "')'>&hellip;</a>";
      }
	  return {
		 "abstract": abstract_display,
         "bib_link": "/pid/"+child_pid,
         "thumbnail": "/thumbnail/"+child_pid,
         "title": source["titlePrincipal"],
         "dateCreated": source["dateCreated"],
         "creator": source["creator"]
      }
   }

  self.initDisplay = function(pid) {
     self.searchResults.removeAll();
	 self.searchMode("browse");
     $.ajax({
            url: "/browse",
            data: {pid: pid},
            method: "POST",
            success: function(data) {
              self.searchResults.removeAll();
              self.facets.removeAll();
	      self.totalHits(data['hits']['total']);
	      self.searchMessage("Browsing <em>" + pid + "</em> contains " + self.totalHits() + " records");
	      for(i in data["hits"]["hits"]) {
                 var row = data["hits"]["hits"][i];
                 self.searchResults.push(self.processResult(row['_source'])); 
              }
	     self.searchResults.sort(function(left,right) {
		 if(left.title == right.title) {
		   return 0;
                  }
		   if(left.title < right.title) {
			 return -1;
		   } else {
			 return 1;
		   }
	     });
             for(i in data["aggregations"]) {
               var agg = data["aggregations"][i];
               self.facets.push(self.processAggregation(i, agg)); 
             }
            
            
	 }		 
    });

  }

  self.facetQuery = function(facet, value) {
     	  self.searchMode("facet");
          var data = {
              mode: self.searchMode(),
              facet: facet,
	      val: value
	  }
          var search_query = self.searchQuery();
          if(search_query) {
             data['q'] = search_query;
          }

	  self.activeFacet(facet);
	  self.activeFacetValue(value);
          var msg = "<strong>" + facet + "</strong> <em>" + value  + "</em>";
	  $.ajax({
		  url: "/search", 
		  method: "GET",
		  data: data,
		  success: function(data) {
                    self.successfulResponse(data, msg);
            }
	  });
  

  }

  self.searchCatalog = function(formElement) {
    var search_type = self.chosenSearch()["search_type"];
    var search_query = self.searchQuery();
    var exact_search = self.exactSearch();
    if (search_query.length < 1) {
       location.reload();
	   return;
    }
    switch(search_type) {

      case "author_search":
          self.searchMode("creator")
	  $.ajax({
            url: '/search',
            data: {q: search_query,
		   mode: self.searchMode(),	
                   type: search_type},
            method: "POST",
            success: function(data) {
                self.successfulResponse(data, "Author search");
            }
	   });
          break;

      case "number_search":
             self.searchMode("number");
       	   $.ajax({
            url: '/search',
            data: {q: search_query,
		   mode: self.searchMode(),	
                   type: search_type},
            method: "POST",
            success: function(data) {
               self.successfulResponse(data, "Number search");
            }
            });
    
           break;

    
      case "search":
	  self.searchMode("keyword");
          $.ajax({
            url: '/search',
            data: {q: search_query,
		   mode: self.searchMode(),	
                   type: search_type},
            method: "POST",
            success: function(data) {
                self.successfulResponse(data, "Your search");
            }
	  });
          break;

      case "subject_search":
          self.searchMode("subject")
       	  $.ajax({
            url: '/search',
            data: {q: search_query,
		   mode: self.searchMode(),	
                   type: search_type},
            method: "POST",
            success: function(data) {
               self.successfulResponse(data, "Subject search");
            }
            });

          break;

      case "title_search":
          self.searchMode("title");
	  $.ajax({
            url: '/search',
            data: {q: search_query,
				   mode: self.searchMode(),	
                   type: search_type},
            method: "POST",
            success: function(data) {
                self.successfulResponse(data, "Title search");
            }
          });
          break;


    }
  }
  self.searchRouting = function() {
    self.searchPlaceholder("Search DigitalCC");
    var search_type = self.chosenSearch()["search_type"];
    switch(search_type) {
       case "number_search":
         self.shouldShowNumber(true);
         self.searchPlaceholder("Search by PID i.e. codu:5454");
         self.exactSearch(true);
         break;

      case "search":
         self.exactSearch(false);
         self.shouldShowNumber(false);
         break;

      default:
         self.shouldShowNumber(false);

    }
  }

  self.successfulResponse = function(data, msg) {
     var search_query = self.searchQuery();
     if(!search_query) {
        search_query = "";
     } 
     self.searchResults.removeAll();
     self.facets.removeAll();
     self.totalHits(data['hits']['total']);
     self.searchMessage(msg + " <em>" + search_query + "</em> returned " + self.totalHits() + " records");
      for(i in data["hits"]["hits"]) {
        var row = data["hits"]["hits"][i];
        self.searchResults.push(self.processResult(row['_source'])); 
      }
      for(i in data["aggregations"]) {
           var agg = data["aggregations"][i];
           self.facets.push(self.processAggregation(i, agg)); 
      }

      self.fromOffset(self.fromOffset() + self.searchResults().length);
  }


  
  
}
