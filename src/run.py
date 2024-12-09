from model import LoadBalancerModel
from visualization import NetworkVisualizer
import pygame
import random

class Button:
    def __init__(self, x, y, width, height, text, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.active_color = (min(color[0] + 30, 255),
                             min(color[1] + 30, 255),
                             min(color[2] + 30, 255))
        self.is_hovered = False

    def draw(self, screen, font):
        color = self.active_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        text_surface = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                return True
        return False


def run_simulation():
    def create_new_model(visualizer):
        return LoadBalancerModel(
            visualizer=visualizer,
            min_users=2,
            max_users=15,
            initial_users=12,
            initial_servers=3,
            max_server_capacity=4,
            user_spawn_chance = 0.5
        )

    # Create visualizer
    vis = NetworkVisualizer()
    model = create_new_model(vis)


    button_height = 40
    button_width = 100
    spacing = 20

    y_position = vis.height - button_height - 20  # Move up from bottom

    start_button = Button(10, y_position, button_width, button_height,
                          "Start", (0, 100, 0))
    pause_button = Button(start_button.rect.right + spacing, y_position,
                          button_width, button_height, "Pause", (100, 100, 0))
    step_button = Button(pause_button.rect.right + spacing, y_position,
                         button_width, button_height, "Step", (150, 0, 150))
    restart_button = Button(step_button.rect.right + spacing, y_position,
                            button_width, button_height, "Restart", (100, 0, 0))
    # Add butterfly effect button
    butterfly_button = Button(
    restart_button.rect.right + spacing, 
    y_position,
    button_width, 
    button_height,
    "Butterfly", 
    (128, 0, 128)  # Purple
    )
    # Add history button
    # history_button = Button(
    #     restart_button.rect.right + spacing, 
    #     y_position,
    #     button_width, 
    #     button_height,
    #     "History", 
    #     (0, 100, 150)  # Blue color
    # )

    print(f"Button positions: Start={start_button.rect}, Pause={
          pause_button.rect}, restart={restart_button.rect}")

    paused = True
    running = True
    show_history = False
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                vis.history_window.close()

            # Handle button clicks
            if start_button.handle_event(event):
                paused = False
                print("Start clicked")
            elif pause_button.handle_event(event):
                paused = True
                print("Pause clicked")
            elif step_button.handle_event(event) and paused:  # Only step when paused
                model.step()  # Execute single step
            elif restart_button.handle_event(event):
                model = create_new_model(vis)  # Create fresh model
                paused = True  # Pause on restart
            elif butterfly_button.handle_event(event):
                if model.server_agents:
                    # Trigger effect on random server
                    server = random.choice(model.server_agents)
                    server.trigger_butterfly_effect()
            # elif history_button.handle_event(event):
            #     print("History button clicked")  # Debug
            #     if vis.previous_frame:
            #         print("Previous frame exists")  # Debug
            #         show_history = not show_history
            #         if show_history:
            #             vis.history_window.show(vis.previous_frame)
            #         else:
            #             vis.history_window.close()
            #     else:
            #         print("No previous frame")

        # Execute model step if not paused
        if not paused:
            model.step()

        # Update visualization
        vis.draw(model)

        # Draw buttons with thick borders
        pygame.draw.rect(vis.screen, (50, 50, 50), start_button.rect, 3)  # Add border
        pygame.draw.rect(vis.screen, (50, 50, 50), step_button.rect, 3)
        pygame.draw.rect(vis.screen, (50, 50, 50), pause_button.rect, 3)
        pygame.draw.rect(vis.screen, (50, 50, 50), restart_button.rect, 3)
        pygame.draw.rect(vis.screen, (50, 50, 50), butterfly_button.rect, 3)
        # pygame.draw.rect(vis.screen, (50, 50, 50), history_button.rect, 3)
        # Draw buttons
        start_button.draw(vis.screen, vis.font)
        step_button.draw(vis.screen, vis.font)
        pause_button.draw(vis.screen, vis.font)
        restart_button.draw(vis.screen, vis.font)
        butterfly_button.draw(vis.screen, vis.font)
        # history_button.draw(vis.screen, vis.font)
        
        pygame.display.flip()
        clock.tick(2)  # 2 FPS for clear visualization

    vis.history_window.close()
    vis.close()


if __name__ == "__main__":
    run_simulation()
