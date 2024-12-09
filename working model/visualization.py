import pygame
import math

class NetworkVisualizer:
    def __init__(self, width=800, height=600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Load Balancer Visualization")
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BLUE = (0, 0, 255)
        self.RED = (255, 0, 0)
        self.YELLOW = (255, 255, 0)
        self.GRAY = (128, 128, 128)
        self.WHITE = (255, 255, 255)
        
        # Fonts
        self.font = pygame.font.Font(None, 24)
        
    def draw(self, model):
        self.screen.fill(self.BLACK)
        
        # Calculate server positions in a circle
        server_count = len(model.server_agents)
        if server_count > 0:
            radius = min(self.width, self.height) * 0.3
            center = (self.width // 2, self.height // 2)
            
            # Draw servers
            server_positions = {}
            for i, server in enumerate(model.server_agents):
                angle = 2 * math.pi * i / server_count
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                server_positions[server.unique_id] = (int(x), int(y))
                
                # Draw server
                color = self.GREEN if server.active else self.RED
                pygame.draw.circle(self.screen, color, (int(x), int(y)), 30)
                
                # Draw server label
                text = self.font.render(f"S{server.unique_id}", True, self.BLACK)
                text_rect = text.get_rect(center=(int(x), int(y)))
                self.screen.blit(text, text_rect)
                
                # Draw load
                load_text = self.font.render(f"{len(server.connected_users)}", True, self.BLACK)
                load_rect = load_text.get_rect(center=(int(x), int(y) + 20))
                self.screen.blit(load_text, load_rect)
            
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
                    pygame.draw.line(self.screen, self.YELLOW, (int(x), int(y)), server_pos, 2)
                
                # Draw user
                color = self.BLUE if user.connected_to is not None else self.GRAY
                pygame.draw.circle(self.screen, color, (int(x), int(y)), user_radius)
        
        # Draw stats
        stats = [
            f"Users: {len(model.user_agents)}",
            f"Servers: {len([s for s in model.server_agents if s.active])}",
            f"Step: {model.step_count}"
        ]
        
        for i, stat in enumerate(stats):
            text = self.font.render(stat, True, self.WHITE)
            self.screen.blit(text, (10, 10 + i * 25))
            
        # pygame.display.flip()
        
    def close(self):
        pygame.quit()