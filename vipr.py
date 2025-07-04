import pygame
import sys
import math
import random

# --- Colors ---
WHITE = ( 255, 255, 255 )
BLACK = ( 0, 0, 0 )
GREY = ( 150, 150, 150 )
NODE_BODY_COLOR = ( 100, 100, 120 )
NODE_BORDER_COLOR = ( 200, 200, 220 )
CONNECTION_COLOR = ( 200, 200, 100 )
SOCKET_COLOR = ( 50, 150, 250 )
INPUT_BOX_COLOR = ( 30, 30, 40 )

class ContextMenu:
    # --- Right-click context menu ---
    def __init__( self, pos, options, all_nodes ):
        self.pos = pos
        self.options = options
        self.all_nodes = all_nodes
        self.rects = []
        self.width = 150
        self.height = len( options ) * 25
        self.menu_rect = pygame.Rect( pos[ 0 ], pos[ 1 ], self.width, self.height )
        self.action_to_perform = None
        self.click_pos = pos

        for i, text in enumerate( options.keys() ):
            rect = pygame.Rect( pos[ 0 ], pos[ 1 ] + i * 25, self.width, 25 )
            self.rects.append( { 'rect': rect, 'text': text } )

    def handle_event( self, event ):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left-click
                for item in self.rects:
                    if item[ 'rect' ].collidepoint( event.pos ):
                        action = self.options[ item[ 'text' ] ]
                        if callable( action ):
                            new_node = action( self.pos )
                            self.all_nodes.append( new_node )
                        return True # Menu was used
            # Any click outside the menu closes it
            if not self.menu_rect.collidepoint( event.pos ):
                return True # Signal to close
        return False

    def draw( self, surface, font ):
        pygame.draw.rect( surface, ( 50, 50, 50 ), self.menu_rect )
        pygame.draw.rect( surface, ( 150, 150, 150 ), self.menu_rect, 1 )
        for item in self.rects:
            # Highlight on hover
            if item[ 'rect' ].collidepoint( pygame.mouse.get_pos() ):
                pygame.draw.rect( surface, ( 80, 80, 100 ), item[ 'rect' ] )

            text_surf = font.render( item[ 'text' ], True, WHITE )
            surface.blit( text_surf, ( item[ 'rect' ].x + 5, item[ 'rect' ].y + 5 ) )

# --- Node Base Class ---
class Node:
    def __init__( self, x, y, width, height, title="Node" ):
        self.rect = pygame.Rect( x, y, width, height )
        self.min_width = 80
        self.min_height = 50
        self.title = title
        self.is_dragging = False
        self.is_resizing = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.id = id( self )

        self.input_sockets = []
        self.output_sockets = []
        self.values = {} # To store computed values for outputs

        # --- Handle for resizing ---
        self.resize_handle_rect = pygame.Rect( self.rect.right - 10, self.rect.bottom - 10, 10, 10)

    def add_input( self, name ):
        self.input_sockets.append( { 'name': name, 'pos': ( 0,0 ), 'rect': None, 'connection': None } )

    def add_output( self, name ):
        self.output_sockets.append( { 'name': name, 'pos': ( 0,0 ), 'rect': None } )
        self.values[ name ] = 0 # Default output value

    def _update_socket_positions( self ):
        # Input sockets on the left
        input_spacing = self.rect.height / ( len( self.input_sockets ) + 1 )
        for i, sock in enumerate( self.input_sockets ):
            sock[ 'pos' ] = ( self.rect.left, self.rect.top + int( input_spacing * ( i + 1 ) ) )
            sock[ 'rect' ] = pygame.Rect( sock[ 'pos' ][ 0 ] - 5, sock[ 'pos' ][ 1 ] - 5, 10, 10 )

        # Output sockets on the right
        output_spacing = self.rect.height / ( len( self.output_sockets ) + 1 )
        for i, sock in enumerate( self.output_sockets ):
            sock[ 'pos' ] = ( self.rect.right, self.rect.top + int( output_spacing * ( i + 1 ) ) )
            sock[ 'rect' ] = pygame.Rect( sock[ 'pos' ][ 0 ] - 5, sock[ 'pos' ][ 1 ] - 5, 10, 10 )

        # Update resize handle position
        self.resize_handle_rect.topleft = ( self.rect.right - 10, self.rect.bottom - 10 )

    def handle_event( self, event, global_state, connections ):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left-click
                # Start resizing
                if self.resize_handle_rect.collidepoint( event.pos ):
                    self.is_resizing = True
                    return True

                # Start a connection from an output socket
                for sock in self.output_sockets:
                    if sock[ 'rect' ].collidepoint( event.pos ):
                        global_state[ 'is_drawing_connection' ] = True
                        global_state[ 'connection_start_node' ] = self
                        global_state[ 'connection_start_socket' ] = sock
                        return True

                # Start dragging the node
                if self.rect.collidepoint( event.pos ):
                    self.is_dragging = True
                    self.drag_offset_x = self.rect.x - event.pos[ 0 ]
                    self.drag_offset_y = self.rect.y - event.pos[ 1 ]
                    return True

            elif event.button == 3: # Right-click
                 # Disconnect an input socket
                 for sock in self.input_sockets:
                    if sock[ 'rect' ].collidepoint( event.pos ) and sock[ 'connection' ] is not None:
                        # Find and remove the connection from the global list
                        for conn in connections[:]:
                            if conn[ 'target_node' ] == self and conn[ 'target_socket' ] == sock:
                                connections.remove( conn )
                                break
                        sock[ 'connection' ] = None # Clear local link
                        return True


        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.is_dragging:
                    self.is_dragging = False
                    return True
                if self.is_resizing:
                    self.is_resizing = False
                    return True


        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                self.rect.x = event.pos[ 0 ] + self.drag_offset_x
                self.rect.y = event.pos[ 1 ] + self.drag_offset_y
                self._update_socket_positions()
                return True
            if self.is_resizing:
                new_width = event.pos[0] - self.rect.left
                new_height = event.pos[1] - self.rect.top
                self.rect.width = max(self.min_width, new_width)
                self.rect.height = max(self.min_height, new_height)
                self._update_socket_positions()
                return True
        return False

    def draw( self, surface, font ):
        # Draw body
        pygame.draw.rect( surface, NODE_BODY_COLOR, self.rect, border_radius=5 )
        pygame.draw.rect( surface, NODE_BORDER_COLOR, self.rect, 2, border_radius=5 )

        # Draw title
        title_surf = font.render( self.title, True, WHITE )
        title_rect = title_surf.get_rect( center=( self.rect.centerx, self.rect.top + 15 ) )
        surface.blit( title_surf, title_rect )

        # Draw sockets
        for sock in self.input_sockets + self.output_sockets:
            pygame.draw.rect( surface, SOCKET_COLOR, sock[ 'rect' ], border_radius=2 )
            pygame.draw.rect( surface, WHITE, sock[ 'rect' ], 1, border_radius=2 )
        
        # Draw resize handle
        pygame.draw.rect(surface, NODE_BORDER_COLOR, self.resize_handle_rect)

    def compute( self ):
        pass

# --- Specific Node Implementations ---
# --- Input nodes ---
class IntegerNode( Node ):
    def __init__( self, x, y, value=1 ):
        super().__init__( x, y, 100, 60, title="Integer" )
        self.value = value
        self.add_output( "out" )
        self._update_socket_positions()
        self.editing = False
        self.input_text = str( self.value )
        self.last_click_time = 0

    def handle_event( self, event, global_state, connections ):
        # --- Handle keyboard input when in edit mode ---
        if self.editing:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        self.value = int( self.input_text )
                    except ValueError:
                        self.value = 0 # Default to 0 if input is invalid
                    self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[ :-1 ]
                else:
                    self.input_text += event.unicode
                return True # Event handled

            if event.type == pygame.MOUSEBUTTONDOWN and not self.rect.collidepoint( event.pos ):
                self.editing = False # Click outside to cancel editing
                self.input_text = str( self.value ) # Revert text
                
        # --- Handle mouse clicks for entering edit mode and standard dragging ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint( event.pos ):
                # Prevent editing when resizing
                if self.resize_handle_rect.collidepoint(event.pos):
                    return super().handle_event(event, global_state, connections)
                current_time = pygame.time.get_ticks()
                # Check for double-click (e.g., within 500 milliseconds)
                if current_time - self.last_click_time < 500:
                    self.editing = True
                    self.input_text = str( self.value )
                    self.is_dragging = False # Prevent dragging on double-click
                    return True # Event handled
                self.last_click_time = current_time

        # --- Fallback to base class event handling (for dragging, etc.) ---
        # Ensure editing mode doesn't interfere with starting a drag
        if not self.editing:
            return super().handle_event( event, global_state, connections )
        return False

    def compute( self ):
        self.values[ "out" ] = self.value

    def draw( self, surface, font ):
        super().draw( surface, font )
        
        if self.editing:
            # --- Draw the input box when editing ---
            input_rect = pygame.Rect( self.rect.centerx - 40, self.rect.centery - 12, 80, 24 )
            pygame.draw.rect( surface, INPUT_BOX_COLOR, input_rect )
            pygame.draw.rect( surface, WHITE, input_rect, 1 )
            
            text_surf = font.render( self.input_text, True, WHITE )
            surface.blit( text_surf, ( input_rect.x + 5, input_rect.y + 5 ) )

            # Blinking cursor
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_pos = input_rect.x + text_surf.get_width() + 8
                pygame.draw.line( surface, WHITE, ( cursor_pos, input_rect.y + 5 ), ( cursor_pos, input_rect.y + 18 ) )
        else:
            # --- Display the value on the node ---
            value_surf = font.render( str( self.value ), True, WHITE )
            value_rect = value_surf.get_rect( center=self.rect.center )
            surface.blit( value_surf, value_rect )

class RndIntegerNode( Node ):
    def __init__( self, x, y, value=1 ):
        super().__init__( x, y, 100, 60, title="Rnd Integer" )
        self.value = random.randint( 0, 65535 )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        self.values[ "out" ] = self.value

    def draw( self, surface, font ):
        super().draw( surface, font )
        
        # --- Display the value on the node ---
        value_surf = font.render( str( self.value ), True, WHITE )
        value_rect = value_surf.get_rect( center=self.rect.center )
        surface.blit( value_surf, value_rect )

class FloatNode( Node ):
    def __init__( self, x, y, value=1 ):
        super().__init__( x, y, 100, 60, title="Float" )
        self.value = value
        self.add_output( "out" )
        self._update_socket_positions()
        self.editing = False
        self.input_text = str( self.value )
        self.last_click_time = 0

    def handle_event( self, event, global_state, connections ):
        # --- Handle keyboard input when in edit mode ---
        if self.editing:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        self.value = float( self.input_text )
                    except ValueError:
                        self.value = 0 # Default to 0 if input is invalid
                    self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[ :-1 ]
                else:
                    self.input_text += event.unicode
                return True # Event handled

            if event.type == pygame.MOUSEBUTTONDOWN and not self.rect.collidepoint( event.pos ):
                self.editing = False # Click outside to cancel editing
                self.input_text = str( self.value ) # Revert text
                
        # --- Handle mouse clicks for entering edit mode and standard dragging ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint( event.pos ):
                # Prevent editing when resizing
                if self.resize_handle_rect.collidepoint(event.pos):
                    return super().handle_event(event, global_state, connections)
                current_time = pygame.time.get_ticks()
                # Check for double-click (e.g., within 500 milliseconds)
                if current_time - self.last_click_time < 500:
                    self.editing = True
                    self.input_text = str( self.value )
                    self.is_dragging = False # Prevent dragging on double-click
                    return True # Event handled
                self.last_click_time = current_time

        # --- Fallback to base class event handling (for dragging, etc.) ---
        # Ensure editing mode doesn't interfere with starting a drag
        if not self.editing:
            return super().handle_event( event, global_state, connections )
        return False

    def compute( self ):
        self.values[ "out" ] = self.value

    def draw( self, surface, font ):
        super().draw( surface, font )
        
        if self.editing:
            # --- Draw the input box when editing ---
            input_rect = pygame.Rect( self.rect.centerx - 40, self.rect.centery - 12, 80, 24 )
            pygame.draw.rect( surface, INPUT_BOX_COLOR, input_rect )
            pygame.draw.rect( surface, WHITE, input_rect, 1 )
            
            text_surf = font.render( self.input_text, True, WHITE )
            surface.blit( text_surf, ( input_rect.x + 5, input_rect.y + 5 ) )

            # Blinking cursor
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_pos = input_rect.x + text_surf.get_width() + 8
                pygame.draw.line( surface, WHITE, ( cursor_pos, input_rect.y + 5 ), ( cursor_pos, input_rect.y + 18 ) )
        else:
            # --- Display the value on the node ---
            value_surf = font.render( str( self.value ), True, WHITE )
            value_rect = value_surf.get_rect( center=self.rect.center )
            surface.blit( value_surf, value_rect )

class RndFloatNode( Node ):
    def __init__( self, x, y, value=1 ):
        super().__init__( x, y, 100, 60, title="Rnd Float" )
        self.value = random.uniform( 0, 65535 )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        self.values[ "out" ] = self.value

    def draw( self, surface, font ):
        super().draw( surface, font )
        
        # --- Display the value on the node ---
        value_surf = font.render( str( self.value ), True, WHITE )
        value_rect = value_surf.get_rect( center=self.rect.center )
        surface.blit( value_surf, value_rect )

class StringNode( Node ):
    def __init__( self, x, y, value=1 ):
        super().__init__( x, y, 100, 60, title="String" )
        self.value = value
        self.add_output( "out" )
        self._update_socket_positions()
        self.editing = False
        self.input_text = str( self.value )
        self.last_click_time = 0

    def handle_event( self, event, global_state, connections ):
        # --- Handle keyboard input when in edit mode ---
        if self.editing:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        self.value = str( self.input_text )
                    except ValueError:
                        self.value = "" # Default to empty string if input is invalid
                    self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[ :-1 ]
                else:
                    self.input_text += event.unicode
                return True # Event handled

            if event.type == pygame.MOUSEBUTTONDOWN and not self.rect.collidepoint( event.pos ):
                self.editing = False # Click outside to cancel editing
                self.input_text = str( self.value ) # Revert text
                
        # --- Handle mouse clicks for entering edit mode and standard dragging ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint( event.pos ):
                # Prevent editing when resizing
                if self.resize_handle_rect.collidepoint(event.pos):
                    return super().handle_event(event, global_state, connections)
                current_time = pygame.time.get_ticks()
                # Check for double-click (e.g., within 500 milliseconds)
                if current_time - self.last_click_time < 500:
                    self.editing = True
                    self.input_text = str( self.value )
                    self.is_dragging = False # Prevent dragging on double-click
                    return True # Event handled
                self.last_click_time = current_time

        # --- Fallback to base class event handling (for dragging, etc.) ---
        # Ensure editing mode doesn't interfere with starting a drag
        if not self.editing:
            return super().handle_event( event, global_state, connections )
        return False

    def compute( self ):
        self.values[ "out" ] = self.value

    def draw( self, surface, font ):
        super().draw( surface, font )
        
        if self.editing:
            # --- Draw the input box when editing ---
            input_rect = pygame.Rect( self.rect.centerx - 40, self.rect.centery - 12, 80, 24 )
            pygame.draw.rect( surface, INPUT_BOX_COLOR, input_rect )
            pygame.draw.rect( surface, WHITE, input_rect, 1 )
            
            text_surf = font.render( self.input_text, True, WHITE )
            surface.blit( text_surf, ( input_rect.x + 5, input_rect.y + 5 ) )

            # Blinking cursor
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_pos = input_rect.x + text_surf.get_width() + 8
                pygame.draw.line( surface, WHITE, ( cursor_pos, input_rect.y + 5 ), ( cursor_pos, input_rect.y + 18 ) )
        else:
            # --- Display the value on the node ---
            value_surf = font.render( str( self.value ), True, WHITE )
            value_rect = value_surf.get_rect( center=self.rect.center )
            surface.blit( value_surf, value_rect )

class ArrayNode( Node ):
    def __init__( self, x, y, value=[ 0 ] ):
        super().__init__( x, y, 100, 60, title="Array" )
        self.value = value
        self.add_output( "out" )
        self._update_socket_positions()
        self.editing = False
        self.input_text = str( self.value )
        self.last_click_time = 0

    def handle_event( self, event, global_state, connections ):
        # --- Handle keyboard input when in edit mode ---
        if self.editing:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        self.value = self.input_text.split( "," )
                    except ValueError:
                        self.value = "" # Default to empty string if input is invalid
                    self.editing = False
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[ :-1 ]
                else:
                    self.input_text += event.unicode
                return True # Event handled

            if event.type == pygame.MOUSEBUTTONDOWN and not self.rect.collidepoint( event.pos ):
                self.editing = False # Click outside to cancel editing
                self.input_text = str( self.value ) # Revert text
                
        # --- Handle mouse clicks for entering edit mode and standard dragging ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint( event.pos ):
                # Prevent editing when resizing
                if self.resize_handle_rect.collidepoint(event.pos):
                    return super().handle_event(event, global_state, connections)
                current_time = pygame.time.get_ticks()
                # Check for double-click (e.g., within 500 milliseconds)
                if current_time - self.last_click_time < 500:
                    self.editing = True
                    self.input_text = str( self.value )
                    self.is_dragging = False # Prevent dragging on double-click
                    return True # Event handled
                self.last_click_time = current_time

        # --- Fallback to base class event handling (for dragging, etc.) ---
        # Ensure editing mode doesn't interfere with starting a drag
        if not self.editing:
            return super().handle_event( event, global_state, connections )
        return False

    def compute( self ):
        self.values[ "out" ] = self.value

    def draw( self, surface, font ):
        super().draw( surface, font )
        
        if self.editing:
            # --- Draw the input box when editing ---
            input_rect = pygame.Rect( self.rect.centerx - 40, self.rect.centery - 12, 80, 24 )
            pygame.draw.rect( surface, INPUT_BOX_COLOR, input_rect )
            pygame.draw.rect( surface, WHITE, input_rect, 1 )
            
            text_surf = font.render( self.input_text, True, WHITE )
            surface.blit( text_surf, ( input_rect.x + 5, input_rect.y + 5 ) )

            # Blinking cursor
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_pos = input_rect.x + text_surf.get_width() + 8
                pygame.draw.line( surface, WHITE, ( cursor_pos, input_rect.y + 5 ), ( cursor_pos, input_rect.y + 18 ) )
        else:
            # --- Display the value on the node ---
            value_surf = font.render( str( self.value ), True, WHITE )
            value_rect = value_surf.get_rect( center=self.rect.center )
            surface.blit( value_surf, value_rect )

# --- Arithmetic nodes ---
class AddNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Add" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "sum" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        val_b = 0
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )

        self.values[ "sum" ] = val_a + val_b

class SubtractNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Subtract" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "difference" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        val_b = 0
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )

        self.values[ "difference" ] = val_a - val_b

class MultiplyNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Multiply" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "product" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        val_b = 0
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )

        self.values[ "product" ] = val_a * val_b

class FullDivideNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Full Divide" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "quotient" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 1
        val_b = 1
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )
        
        if val_b != 0:
            self.values[ "quotient" ] = val_a / val_b
        else:
            self.values[ "quotient" ] = "Error"

class ModDivideNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Mod Divide" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "remainder" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 1
        val_b = 1
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )
        
        if val_b != 0:
            self.values[ "remainder" ] = val_a % val_b
        else:
            self.values[ "remainder" ] = "Error"

class IntDivideNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Int Divide" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "quotient" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 1
        val_b = 1
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )
        
        if val_b != 0:
            self.values[ "quotient" ] = val_a // val_b
        else:
            self.values[ "quotient" ] = "Error"

class ExponentNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Exponent" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 1
        val_b = 1
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )
        
        self.values[ "out" ] = val_a ** val_b

class AbsNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 130, 50, title="Absolute Value" )
        self.add_input( "A" )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 1
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        
        self.values[ "out" ] = abs( val_a )

# --- Logic nodes ---
class AndNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="And" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        val_b = 0
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )
        
        self.values[ "out" ] = val_a and val_b

class OrNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Or" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        val_b = 0
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )
        
        self.values[ "out" ] = val_a or val_b
        
class XorNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Xor" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        val_b = 0
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )
        
        self.values[ "out" ] = val_a ^ val_b

class NotNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Not" )
        self.add_input( "in" )
        self.add_output( "out" )
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        
        self.values[ "out" ] = not val_a

# --- String nodes ---
class ConcatNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 50, title="Concatenate" )
        self.add_input( "A" )
        self.add_input( "B" )
        self.add_output( "new_string" )
        self._update_socket_positions()

    def compute( self ):
        val_a = ""
        val_b = ""
        # Get value from input A connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_a = source_node.values.get( source_socket_name, 0 )
        # Get value from input B connection
        if self.input_sockets[ 1 ][ 'connection' ]:
            source_node = self.input_sockets[ 1 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 1 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            val_b = source_node.values.get( source_socket_name, 0 )

        self.values[ "new_string" ] = val_a + val_b

# --- Output nodes ---
class DisplayNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 60, title="Display" )
        self.add_input( "in" )
        self.display_value = "None"
        self._update_socket_positions()

    def compute( self ):
        # Get value from the input connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            self.display_value = source_node.values.get( source_socket_name, "None" )
        else:
            self.display_value = "None"

    def draw( self, surface, font ):
        super().draw( surface, font )
        # Display the computed value on the node
        display_text = str( self.display_value )
        if isinstance(self.display_value, float):
             display_text = f"{self.display_value:.2f}" # Format floats nicely

        value_surf = font.render( display_text, True, WHITE )
        value_rect = value_surf.get_rect( center=self.rect.center )
        surface.blit( value_surf, value_rect )
        
class PreviewNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 60, title="Preview" )
        self.add_input( "in" )
        self.add_output( "out" )
        self.display_value = "None"
        self._update_socket_positions()

    def compute( self ):
        val_a = 0
        # Get value from the input connection
        if self.input_sockets[ 0 ][ 'connection' ]:
            source_node = self.input_sockets[ 0 ][ 'connection' ][ 'source_node' ]
            source_socket_name = self.input_sockets[ 0 ][ 'connection' ][ 'source_socket' ][ 'name' ]
            self.display_value = source_node.values.get( source_socket_name, "None" )
            val_a = source_node.values.get( source_socket_name, 0 )
        else:
            self.display_value = "None"
        
        self.values[ "out" ] = val_a

    def draw( self, surface, font ):
        super().draw( surface, font )
        # Display the computed value on the node
        display_text = str( self.display_value )
        if isinstance(self.display_value, float):
             display_text = f"{self.display_value:.2f}" # Format floats nicely

        value_surf = font.render( display_text, True, WHITE )
        value_rect = value_surf.get_rect( center=self.rect.center )
        surface.blit( value_surf, value_rect )

# --- Main Application ---
def main():
    pygame.init()
    pygame.font.init()
    font = pygame.font.SysFont( None, 24 )
    small_font = pygame.font.SysFont( None, 20 )

    SCREEN_WIDTH = 1200
    SCREEN_HEIGHT = 800
    screen = pygame.display.set_mode( ( SCREEN_WIDTH, SCREEN_HEIGHT ) )
    pygame.display.set_caption( "ViPr - Visual Programmer" )

    nodes = [ # --- Default nodes on opening ---
        IntegerNode( 100, 100, value=5 ),
        IntegerNode( 100, 250, value=10 ),
        AddNode( 350, 150 ),
        DisplayNode( 600, 150 )
    ]
    connections = []

    global_connection_state = {
        'is_drawing_connection': False,
        'connection_start_node': None,
        'connection_start_socket': None,
    }
    
    context_menu = None
    
    # --- Track which node is being edited ---
    editing_node = None

    running = True
    clock = pygame.time.Clock()

    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        # --- Determine which node is being edited ---
        editing_node = None
        for n in nodes:
            if isinstance( n, (IntegerNode, FloatNode, StringNode, ArrayNode) ) and n.editing:
                editing_node = n
                break

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            # --- Pass keyboard events to the editing node FIRST ---
            if editing_node:
                editing_node.handle_event( event, global_connection_state, connections )
                # If a click happens, check if it's outside the editing node to close it
                if event.type == pygame.MOUSEBUTTONDOWN and not editing_node.rect.collidepoint( event.pos ):
                    editing_node.editing = False
                    editing_node.input_text = str( editing_node.value ) # revert
                continue # Skip other handlers if we are editing

            # --- DELETE NODE with Delete Key ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DELETE:
                    node_to_delete = None
                    for node in nodes:
                        if node.rect.collidepoint( mouse_pos ):
                            node_to_delete = node
                            break # Found the node to delete
                    
                    if node_to_delete:
                        # Remove connections associated with this node
                        connections[:] = [ c for c in connections if c[ 'source_node' ] != node_to_delete and c[ 'target_node' ] != node_to_delete ]
                        
                        # Unlink from any nodes that were targeting it
                        for n in nodes:
                            if n == node_to_delete: continue
                            for s in n.input_sockets:
                                if s[ 'connection' ] and s[ 'connection' ][ 'source_node' ] == node_to_delete:
                                    s[ 'connection' ] = None
                        
                        nodes.remove( node_to_delete )
                        continue # Event handled

            # --- Context Menu Handling ---
            if context_menu:
                if context_menu.handle_event( event ):
                    context_menu = None # Close menu after action
                    continue # Skip other event handling

            # --- Finalize Connection ---
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and global_connection_state[ 'is_drawing_connection' ]:
                target_found = False
                for node in nodes:
                    for sock in node.input_sockets:
                        if sock[ 'rect' ].collidepoint( event.pos ) and sock[ 'connection' ] is None:
                            # Create connection
                            new_conn = {
                                'source_node': global_connection_state[ 'connection_start_node' ],
                                'source_socket': global_connection_state[ 'connection_start_socket' ],
                                'target_node': node,
                                'target_socket': sock
                            }
                            connections.append( new_conn )
                            sock[ 'connection' ] = new_conn # Link locally
                            target_found = True
                            break
                    if target_found: break
                
                # Reset connection drawing state
                global_connection_state[ 'is_drawing_connection' ] = False
                global_connection_state[ 'connection_start_node' ] = None
                global_connection_state[ 'connection_start_socket' ] = None
                continue

            # --- Open Context Menu ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                # Prevent menu if clicking on a node's socket
                on_socket = False
                for node in nodes:
                    for sock in node.input_sockets + node.output_sockets:
                        if sock[ 'rect' ].collidepoint( event.pos ):
                           on_socket = True
                           break
                    if on_socket: break
                
                if not on_socket:
                    context_menu = ContextMenu(event.pos, { # --- Add context menu items here ---
                        "Integer": lambda pos: IntegerNode( pos[ 0 ], pos[ 1 ], value=0 ),
                        "Random Integer": lambda pos: RndIntegerNode( pos[ 0 ], pos[ 1 ], value=0 ),
                        "Float": lambda pos: FloatNode( pos[ 0 ], pos[ 1 ], value=0.0 ),
                        "RndFloat": lambda pos: RndFloatNode( pos[ 0 ], pos[ 1 ], value=0.0 ),
                        "String": lambda pos: StringNode( pos[ 0 ], pos[ 1 ], value="" ),
                        "Array": lambda pos: ArrayNode( pos[ 0 ], pos[ 1 ], value=[0] ),
                        "Add": lambda pos: AddNode( pos[ 0 ], pos[ 1 ] ),
                        "Subtract": lambda pos: SubtractNode( pos[ 0 ], pos[ 1 ] ),
                        "Multiply": lambda pos: MultiplyNode( pos[ 0 ], pos[ 1 ] ),
                        "Full Divide": lambda pos: FullDivideNode( pos[ 0 ], pos[ 1 ] ),
                        "Mod Divide": lambda pos: ModDivideNode( pos[ 0 ], pos[ 1 ] ),
                        "Int Divide": lambda pos: IntDivideNode( pos[ 0 ], pos[ 1 ] ),
                        "Exponent": lambda pos: ExponentNode( pos[ 0 ], pos[ 1 ] ),
                        "Absolute Value": lambda pos: AbsNode( pos[ 0 ], pos[ 1 ] ),
                        "And": lambda pos: AndNode( pos[ 0 ], pos[ 1 ] ),
                        "Or": lambda pos: OrNode( pos[ 0 ], pos[ 1 ] ),
                        "Xor": lambda pos: XorNode( pos[ 0 ], pos[ 1 ] ),
                        "Not": lambda pos: NotNode( pos[ 0 ], pos[ 1 ] ),
                        "Concatenate": lambda pos: ConcatNode( pos[ 0 ], pos[ 1 ] ),
                        "Display": lambda pos: DisplayNode( pos[ 0 ], pos[ 1 ] ),
                        "Preview": lambda pos: PreviewNode( pos[ 0 ], pos[ 1 ] )
                    }, nodes )
                    continue

            # --- Pass events to nodes ---
            for node in reversed( nodes ):
                if node.handle_event( event, global_connection_state, connections ):
                    break

        # --- Update & Compute ---
        # A simple, iterative computation model. For complex graphs, a topological sort would be needed.
        for _ in range( len( nodes ) ): # Iterate a few times to propagate changes
            for node in nodes:
                node.compute()

        # --- Drawing ---
        screen.fill( GREY )

        # Draw established connections
        for conn in connections:
            start_pos = conn[ 'source_socket' ][ 'pos' ]
            end_pos = conn[ 'target_socket' ][ 'pos' ]
            pygame.draw.line( screen, CONNECTION_COLOR, start_pos, end_pos, 2 )
            pygame.draw.aaline( screen, WHITE, start_pos, end_pos )

        # Draw temporary connection line
        if global_connection_state[ 'is_drawing_connection' ]:
            start_pos = global_connection_state[ 'connection_start_socket' ][ 'pos' ]
            pygame.draw.line( screen, CONNECTION_COLOR, start_pos, mouse_pos, 3 )

        # Draw all nodes
        for node in nodes:
            node.draw( screen, font )
        
        # Draw context menu if active
        if context_menu:
            context_menu.draw( screen, small_font )

        # --- Update Display ---
        pygame.display.flip()
        clock.tick( 60 )

    # --- Cleanup ---
    pygame.font.quit()
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()