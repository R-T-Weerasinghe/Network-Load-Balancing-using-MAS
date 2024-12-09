import pygame
import math
import pygame.surface



class HistoryWindow:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.window = None
        
    def show(self, previous_frame):
        """Create window and show previous frame."""
        if previous_frame is None:
            return
            
        try:
            # Create new window
            pygame.init()
            self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
            pygame.display.set_caption("History View")
            
            # Clear and draw
            self.window.fill((0, 0, 0))
            self.window.blit(previous_frame, (0, 0))
            pygame.display.update()
            
        except pygame.error as e:
            print(f"Error creating history window: {e}")
    
    def close(self):
        """Close history window."""
        if self.window:
            pygame.display.quit()
            self.window = None

class NetworkVisualizer:
    def __init__(self, width=1200, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.previous_frame = None
        self.history_window = HistoryWindow(width, height)
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Load Balancer Visualization")
        self.message_log = []  # Store last N messages
        self.max_messages = 16  # Number of messages to show
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.GREEN = (0, 100, 0)
        self.BLUE = (0, 0, 255)
        self.RED = (255, 0, 0)
        self.YELLOW = (255, 255, 0)
        self.GRAY = (128, 128, 128)
        self.WHITE = (255, 255, 255)
        self.ORANGE = (255, 165, 0)
        
        # Fonts
        self.font = pygame.font.Font(None, 24)

    def draw_legend(self, screen):
        # Legend position and settings
        legend_x = self.width - 150  # Right side
        legend_y = 20  # Top
        circle_radius = 10
        text_offset = 25
        line_height = 30
        
        # Draw User legend
        pygame.draw.circle(screen, self.BLUE, (legend_x, legend_y), circle_radius)
        user_text = self.font.render("User", True, self.BLACK)
        screen.blit(user_text, (legend_x + text_offset, legend_y - circle_radius))
        
        # Draw Server legend
        pygame.draw.circle(screen, self.GREEN, (legend_x, legend_y + line_height), circle_radius)
        server_text = self.font.render("Server", True, self.BLACK)
        screen.blit(server_text, (legend_x + text_offset, legend_y + line_height - circle_radius))

    def capture_frame(self):
        """Capture current frame."""
        self.previous_frame = self.screen.copy()
        
    def add_log_message(self, message):
        """Add message to log with timestamp."""
        self.message_log.append(message)
        if len(self.message_log) > self.max_messages:
            self.message_log.pop(0)
            

    def draw(self, model):
        # Capture frame before drawing new one
        self.capture_frame()

        self.screen.fill(self.WHITE)
        
        # Calculate server positions in a circle
        server_count = len(model.server_agents)
        if server_count > 0:
            radius = min(self.width, self.height) * 0.3
            center = (self.width // 3, self.height // 2)
            
            # Draw servers
            server_positions = {}
            for i, server in enumerate(model.server_agents):
                angle = 2 * math.pi * i / server_count
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                server_positions[server.unique_id] = (int(x), int(y))
                
            
            # Draw users and connections
            user_radius = 10
            for i, user in enumerate(model.user_agents):
                # Calculate user position (spread around the center)
                angle = 2 * math.pi * i / len(model.user_agents)
                small_radius = radius * 0.5
                x = center[0] + small_radius * math.cos(angle)
                y = center[1] + small_radius * math.sin(angle)
                
                # Draw connection line if connected
                if user.connected_to is not None and user.connected_to in server_positions:
                    server_pos = server_positions[user.connected_to]
                    pygame.draw.line(self.screen, self.ORANGE, (int(x), int(y)), server_pos, 2)
                
                # Draw user
                color = self.BLUE if user.connected_to is not None else self.GRAY
                pygame.draw.circle(self.screen, color, (int(x), int(y)), user_radius)
            
            # Draw the rest of servers
            for i, server in enumerate(model.server_agents):
                x, y = server_positions[server.unique_id]
                # Draw server
                color = self.GREEN if server.active else self.RED
                pygame.draw.circle(self.screen, color, (int(x), int(y)), 30)
                
                # Draw server label
                text = self.font.render(f"S{server.unique_id}", True, self.WHITE)
                text_rect = text.get_rect(center=(int(x), int(y)))
                self.screen.blit(text, text_rect)
                
                # Draw load
                load_text = self.font.render(f"{len(server.connected_users)}", True, self.WHITE)
                load_rect = load_text.get_rect(center=(int(x), int(y) + 20))
                self.screen.blit(load_text, load_rect)
        
        # Draw stats
        stats = [
            f"Users: {len(model.user_agents)}",
            f"Servers: {len([s for s in model.server_agents if s.active])}",
            f"Step: {model.step_count}"
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, self.BLACK)
            self.screen.blit(text, (10, 10 + i * 25))
        
        # Draw message log in bottom right
        start_y = self.height - (self.max_messages * 25) - 60  # Above buttons
        for i, msg in enumerate(self.message_log):
            text = self.font.render(msg, True, self.BLACK)
            self.screen.blit(text, (self.width - 500, start_y + i * 25))
        
        self.draw_legend(self.screen)

    def close(self):
        pygame.quit()