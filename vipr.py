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
    """
    A base class for a draggable, connectable block in the visual language.
    Handles drawing, dragging, and socket management.
    """
    def __init__( self, x, y, width, height, title="Node" ):
        self.rect = pygame.Rect( x, y, width, height )
        self.title = title
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.id = id( self )

        self.input_sockets = []
        self.output_sockets = []
        self.values = {} # To store computed values for outputs

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

    def handle_event( self, event, global_state, connections ):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left-click
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
            if event.button == 1 and self.is_dragging:
                self.is_dragging = False
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                self.rect.x = event.pos[ 0 ] + self.drag_offset_x
                self.rect.y = event.pos[ 1 ] + self.drag_offset_y
                self._update_socket_positions()
                return True
        return False

    def draw( self, surface, font ):
        """Draws the node body, title, and sockets."""
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

    def compute( self ):
        """
        Placeholder for computation logic.
        To be implemented by derived node classes.
        """
        pass

# --- Specific Node Implementations ---
class ValueNode( Node ):
    def __init__( self, x, y, value=1 ):
        super().__init__( x, y, 100, 60, title="Value" )
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

class AddNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 80, title="Add" )
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
        super().__init__( x, y, 100, 80, title="Subtract" )
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
        super().__init__( x, y, 100, 80, title="Multiply" )
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

class DivisionNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 80, title="Divide" )
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
            self.values[ "quotient" ] = "Error" # Handle division by zero

class ModuloNode( Node ):
    def __init__( self, x, y ):
        super().__init__( x, y, 100, 80, title="Modulo" )
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
        ValueNode( 100, 100, value=5 ),
        ValueNode( 100, 250, value=10 ),
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
            if isinstance( n, ValueNode ) and n.editing:
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
                    context_menu = ContextMenu(event.pos, {
                        "Value": lambda pos: ValueNode( pos[ 0 ], pos[ 1 ], value=0 ),
                        "Add": lambda pos: AddNode( pos[ 0 ], pos[ 1 ] ),
                        "Subtract": lambda pos: SubtractNode( pos[ 0 ], pos[ 1 ] ),
                        "Multiply": lambda pos: MultiplyNode( pos[ 0 ], pos[ 1 ] ),
                        "Division": lambda pos: DivisionNode( pos[ 0 ], pos[ 1 ] ),
                        "Modulo": lambda pos: ModuloNode( pos[ 0 ], pos[ 1 ] ),
                        "Display": lambda pos: DisplayNode( pos[ 0 ], pos[ 1 ] )
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